"""
This software has been approved for release by the U.S. Geological Survey
(USGS). Although the software has been subjected to rigorous review, the USGS
reserves the right to update the software as needed pursuant to further
analysis and review. No warranty, expressed or implied, is made by the USGS or
the U.S. Government as to the functionality of the software and related
material nor shall the fact of release constitute any such warranty.
Furthermore, the software is released on condition that neither the USGS nor
the U.S. Government shall be held liable for any damages resulting from its
authorized or unauthorized use.

Author:         Steve Foga
Affiliation:    SGT Inc., contractor to USGS EROS Center
Contact:        steven.foga.ctr@usgs.gov
Created:        15 May 2017
Version:        1.2

Changelog
1.0     15 May 2017     Original development with Python 2.7.10 and
                        ArcGIS 10.4.1.
1.1     09 Aug 2017     Update to handle any L8 pixel_qa terrain occlusion.
1.2     21 Aug 2017     Now decodes bits directly, instead of lookup table.
"""
import sys
import os
import arcpy
import lookup_dict


def build_attr_table(raster_in, sensor, band, rm_low=False):
    """
    Build attribute table for thematic raster using pre-defined dictionary.

    :param raster_in: <str> Path to target raster.
    :param sensor: <str> Sensor type.
    :param band: <str> Band type.
    :param rm_low: <bool> Remove (True) or keep (False) 'low' values (excludes
                          sr_aerosol, radiometric sat. in BQA)
    :return:
    """
    # read lookup dictionary
    bit_flags = lookup_dict.bit_flags

    # check to ensure raster is not floating/double/complex
    vt = int(str(arcpy.GetRasterProperties_management(raster_in, "VALUETYPE")))
    if vt >= 9:
        arcpy.AddError("ERROR: Data type of input raster must be integer.")
        sys.exit()

    # build attribute table
    arcpy.BuildRasterAttributeTable_management(raster_in, "Overwrite")

    # add description field to table
    arcpy.AddField_management(raster_in, "Descr", "TEXT", "", "", 120)
    fields = ("Value", "Descr")

    # re-map input sensor name to qa_values sensor name
    if sensor == 'Landsat 4-5, 7':
        sens = 'L47'
    elif sensor == 'Landsat 8':
        sens = 'L8'
    else:
        arcpy.AddError("ERROR: Incorrect sensor provided. Input: {0}; "
                       "Potential options: Landsat 4-5, 7 | Landsat 8"
                       .format(sensor))

    # assign values to attribute table
    with arcpy.da.UpdateCursor(raster_in, fields) as cursor:
        for row in cursor:
            # check all possible bits for match with target value (row[0])
            bit_values = sorted(bit_flags[band][sens].values())
            bit_bool = []
            for bv in bit_values:
                if len(bv) == 1:  # single bit
                    bit_bool.append(row[0] & 1 << bv[0] > 0)

                elif len(bv) > 1:  # 2+ bits
                    bits = []
                    for b in bv:
                        bits.append(row[0] & 1 << b > 0)
                    if all(item == True for item in bits):
                        bit_bool.append(True)
                    else:
                        bit_bool.append(False)

                else:
                    sys.exit("No valid bits found for target band.")

            # create description of each value based upon all possible bits
            true_bits = [i for (i, bb) in zip(bit_values, bit_bool) if bb]

            # if double bits exist, eliminate single bit descriptions,
            #   otherwise, the descriptions will duplicate themselves.
            bb_double = [len(i) > 1 for i in true_bits]
            if any(bb_double):
                # get only the double bits
                dbit_nest = [i for (i, db) in zip(true_bits, bb_double) if db]

                # collapse the bits into a single list
                dbits = [item for sublist in dbit_nest for item in sublist]

                # remove matching single bits out of true_bits list
                tbo = []
                for t in true_bits:
                    tb_out = []
                    for d in dbits:
                        if t[0] != d or len(t) > 1:
                            tb_out.append(True)
                        else:
                            tb_out.append(False)
                    if all(tb_out):
                        tbo.append(t)

                # replace true_bits with filtered list
                true_bits = tbo

            def get_label(bits):
                """
                Generate label for value in attribute table.

                :param bits: <list> List of True or False for bit position
                :return: <str> Attribute label
                """
                if len(bits) == 0:
                    if band == 'radsat_qa':
                        return 'No Saturation'

                    elif band == 'sr_cloud_qa' or band == 'sr_aerosol':
                        return 'None'

                    elif band == 'BQA':
                        return 'Not Determined'

                # build description from all bits represented in value
                desc = []
                for tb in bits:
                    k = next(key for key, value in
                             bit_flags[band][sens].items() if value == tb)

                    # if 'low' labels are disabled, do not add them here
                    if rm_low and band != 'BQA' and 'low' in k.lower():
                        continue

                    # if last check, and not radiometric sat, set to 'clear'
                    elif rm_low and band == 'BQA' and 'low' in k.lower() and \
                                    tb == bits[-1] and \
                                    'radiometric' not in k.lower() and \
                            not desc:
                        k = 'Clear'

                    # if BQA and bit is low radiometric sat, keep it
                    elif rm_low and band == 'BQA' and 'low' in k.lower():
                        if 'radiometric' not in k.lower():
                            continue

                    # if radsat_qa, handle differently to make display cleaner
                    if band == 'radsat_qa':
                        if not desc:
                            desc = "Band {0} Data Saturation".format(tb[0])

                        else:
                            desc = "{0},{1} Data Saturation".format(
                                desc[:desc.find('Data') - 1], tb[0])

                    # string creation for all other bands
                    else:
                        if not desc:
                            desc = "{0}".format(k)

                        else:
                            desc += ", {0}".format(k)

                # final check to make sure something was set
                if not desc:
                    desc = 'ERROR: bit set incorrectly'

                return desc

            # add desc to row description (row[1])
            try:
                row[1] = get_label(true_bits)
            except UnboundLocalError:
                row[1] = 'ERROR: bit read incorrectly'

            # update table row
            cursor.updateRow(row)

    # if running in ArcMap, refresh display in current mxd
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
    except RuntimeError:
        pass
    else:
        # get current (active) data frame
        df = mxd.activeDataFrame

        # find source layer (if it exists)
        try:
            source_lyr = arcpy.mapping.ListLayers(mxd,
                                                  raster_in.split(os.sep)[-1],
                                                  df)[0]
        except IndexError:
            pass

        # create target layer
        raster_fname, ext = os.path.splitext(raster_in.split(os.sep)[-1])
        result = arcpy.MakeRasterLayer_management(raster_in,
                                                  raster_fname + ext)
        layer = result.getOutput(0)

        # add new layer
        arcpy.mapping.AddLayer(df, layer, "AUTO_ARRANGE")

        # remove old layer (if it exists)
        try:
            arcpy.mapping.RemoveLayer(df, source_lyr)
        except (UnboundLocalError, NameError):
            pass

        arcpy.RefreshTOC()
