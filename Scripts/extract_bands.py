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
Created:        20 June 2017
Version:        2.0

Changelog
1.0     15 May 2017     DNE in this release.
2.0     20 Jun 2017     Original development.
"""
import sys
import os
import arcpy
import lookup_dict


def extract_bits_from_band(raster_in, sensor, band, output_bands, basename,
                           combine_layers=False):
    """
    Pull specific class(es) from bit-packed band, return discrete band(s).

    :param raster_in: <str> Path to input raster.
    :param sensor: <str> Sensor type, as either "L8" or "L47".
    :param band: <str> Band type.
    :param output_bands: <list> Name(s) of bit(s) to be extracted.
    :param basename: <str> Base filename for output data.
    :param combine_layers: <bool> Combine all extracted bits to single band.

    :return:
    """

    def con_raster(in_raster, out_raster, out_values):
        """
        Create binary raster based on occurrence of specific value(s).

        :param in_raster: <Raster> Single band in ArcGIS Raster format.
        :param out_raster: <str> Path + filename for output raster.
        :param out_values: <list> Values to produce a positive result.
        :return:
        """

        def build_con_statement(values):
            """
            Create SQL string with multiple conditions for arcpy.sa.Con().

            :param values: <list> List of integers to be extracted.
            :return: <str> SQL string to be passed to conditional function.
            """
            str_out = ""
            for vv in range(len(values)):
                if vv < max(range(len(values))):
                    str_out += "Value = {0} Or ".format(values[vv])
                else:
                    str_out += "Value = {0}".format(values[vv])

            return str_out

        # use conditional function to make binary raster
        out = arcpy.sa.Con(in_raster, 1, 0, build_con_statement(out_values))

        # set pixel depth to 8-bit unsigned and save to file
        arcpy.CopyRaster_management(out, out_raster,
                                    pixel_type="8_BIT_UNSIGNED")

    # verify Spatial Analyst licence is available
    class LicenseError(Exception):
        pass

    try:
        if arcpy.CheckExtension("Spatial") == "Available":
            arcpy.CheckOutExtension("Spatial")
        else:
            # raise a custom exception
            raise LicenseError

    except LicenseError:
        print("Spatial Analyst license is unavailable")
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))

    # read lookup dictionary
    bit_flags = lookup_dict.bit_flags

    # read raster
    r_in = arcpy.Raster(raster_in)

    # check to ensure raster is not floating/double/complex
    vt = int(str(arcpy.GetRasterProperties_management(r_in, "VALUETYPE")))
    if vt >= 9:
        arcpy.AddError("ERROR: Data type of input raster must be integer.")
        sys.exit()

    # determine input band extension
    input_ext = os.path.splitext(raster_in)[-1]

    # build attribute table
    arcpy.BuildRasterAttributeTable_management(r_in)

    # get unique values
    unique_vals = []
    with arcpy.da.SearchCursor(raster_in, ("Value")) as cursor:
        for row in cursor:
            unique_vals.append(row[0])

    # pull target values from each requested output band
    output_vals_all = []
    for bv in output_bands:
        # clean up double quotes from bv, if necessary
        if bv.startswith('"') and bv.endswith('"'):
            bv = bv[1:-1]

        # get bit value
        bit_value = bit_flags[band][sensor][bv]

        # use bit logic to return only target values
        bit_bool = []
        for v in unique_vals:
            if len(bit_value) == 1:  # single bit
                bit_bool.append(v & 1 << bit_value[0] > 0)

            elif len(bit_value) > 1:  # 2+ bits
                bits = []
                for b in bit_value:
                    bits.append(v & 1 << b > 0)
                if all(item == True for item in bits):
                    bit_bool.append(True)
                else:
                    bit_bool.append(False)

            else:
                sys.exit("No valid bits found for target band.")

        # return raster values that match bit(s)
        output_vals = [i for (i, bl) in zip(unique_vals, bit_bool) if bl]

        if combine_layers:
            output_vals_all.extend(output_vals)

        else:  # write out raster now, instead of single raster later
            # create output raster name
            raster_out = basename + "_" + bv.lower().replace(' ', '_') + \
                         input_ext

            # generate new raster
            con_raster(raster_in, raster_out, output_vals)

    # use all output values to create single binary band
    if combine_layers:
        # create output raster name
        raster_out = basename + "_combine" + input_ext

        # generate new raster
        con_raster(raster_in, raster_out, output_vals_all)

        # if running in ArcMap, load band to current Data Frame
        try:
            mxd = arcpy.mapping.MapDocument("CURRENT")
        except RuntimeError:
            pass
        else:
            # get current (active) data frame
            df = mxd.activeDataFrame

            # add new layer
            arcpy.mapping.AddLayer(df, raster_out, "AUTO_ARRANGE")

            arcpy.RefreshTOC()

        print(arcpy.GetMessages())
        arcpy.GetMessages()
