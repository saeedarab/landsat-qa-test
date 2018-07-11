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
import arcpy
import extract_bands
import lookup_dict


class ExtractBands(object):
    def __init__(self):
        """
        Define the tool (tool name is the name of the class).
        """
        #import lookup_dict
        #self.bit_flags = lookup_dict.bit_flags

        self.label = "Extract QA Bands"
        self.description = ""
        self.params = arcpy.GetParameterInfo()
        self.canRunInBackground = True

    def get_sensor(self, input_sen):
        """
        Convert input (display) sensor name to internal sensor name.

        :param input_sen: <str> Input sensor name
        :return: <str>
        """
        if input_sen == "Landsat 8":
            return "L8"
        elif input_sen == "Landsat 4-5, 7":
            return "L47"
        else:
            sys.exit("{0} is not a valid input sensor.".format(input_sen))

    def get_bit_keys(self, input_band, input_sensor, input_dict):
        """
        Return list of keys from dictionary, sorted by value.

        :param input_band: <str> Name of input band.
        :param input_sensor: <str> Name of input sensor.
        :param input_dict: <dict> Key:value pairs.
        :return: <list> Keys sorted by value.
        """
        # convert input_sensor to input_dict's designation
        in_sen = self.get_sensor(input_sensor)

        # get specific key:values
        kv_pairs = input_dict[input_band][in_sen]

        return sorted(kv_pairs, key=kv_pairs.get)

    def getParameterInfo(self):
        """
        Input parameter interface for Arc Toolbox.

        :return: <list> Input parameters
        """
        # First parameter (input raster)
        param0 = arcpy.Parameter(
            displayName="Input Raster Layer",
            name="in_raster",
            datatype="DERasterBand",
            parameterType="Required",
            direction="Input")

        # Second parameter (input sensor)
        param1 = arcpy.Parameter(
            displayName="Sensor",
            name="sensor",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ['Landsat 8',
                              'Landsat 4-5, 7']

        # Third parameter (input band)
        param2 = arcpy.Parameter(
            displayName="Band",
            name="band",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ['BQA',
                              'pixel_qa',
                              'radsat_qa'
                              'sr_aerosol',
                              'sr_cloud_qa']

        # Fourth parameter (target QA layers, now empty)
        param3 = arcpy.Parameter(
            displayName="QA Layers",
            name="qa_layers",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True)

        # Fifth parameter (combine y/n)
        param4 = arcpy.Parameter(
            displayName="Combine",
            name="combine_layers",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        # Sixth parameter (output path)
        param5 = arcpy.Parameter(
            displayName="Output Raster Path and Basename",
            name="out_raster",
            datatype="DEFile",
            parameterType="Required",
            direction="Output")

        params = [param0, param1, param2, param3, param4, param5]
        return params

    def updateParameters(self, parameters):
        """
        Set default values in Arc Toolbox interface based on input band.

        :param parameters: <list> Input parameters
        :return:
        """
        # read lookup dictionary
        bit_flags = lookup_dict.bit_flags

        # Change sensor in drop-down
        if parameters[0].valueAsText and not parameters[1].altered:
            if [s for s in ['LE07', 'LT05', 'LT04'] if
                s in parameters[0].valueAsText]:
                parameters[1].value = 'Landsat 4-5, 7'

            elif [s for s in ['LC08', 'LT08', 'LO08'] if
                  s in parameters[0].valueAsText]:
                parameters[1].value = 'Landsat 8'

        # Restrict band options based upon sensor
        if parameters[1].valueAsText and not parameters[2].altered:
            if parameters[1].value == 'Landsat 8':
                parameters[2].filter.list = ['BQA',
                                             'pixel_qa',
                                             'radsat_qa',
                                             'sr_aerosol']

            elif parameters[1].value == 'Landsat 4-5, 7':
                parameters[2].filter.list = ['BQA',
                                             'pixel_qa',
                                             'radsat_qa',
                                             'sr_cloud_qa']

        # Change band in drop-down
        if parameters[0].valueAsText and not parameters[2].altered:
            if [b for b in ['bqa', 'BQA'] if
                b in parameters[0].valueAsText]:
                parameters[2].value = 'BQA'
            elif [b for b in ['pixel_qa', 'PIXELQA'] if
                  b in parameters[0].valueAsText]:
                parameters[2].value = 'pixel_qa'
            elif [b for b in ['radsat_qa', 'RADSATQA'] if
                  b in parameters[0].valueAsText]:
                parameters[2].value = 'radsat_qa'
            elif [b for b in ['sr_aerosol', 'SRAEROSOLQA'] if
                  b in parameters[0].valueAsText]:
                parameters[2].value = 'sr_aerosol'
            elif [b for b in ['sr_cloud_qa', 'SRCLOUDQA'] if
                  b in parameters[0].valueAsText]:
                parameters[2].value = 'sr_cloud_qa'

        # Populate QA Layers based upon band-sensor combination
        if parameters[1].valueAsText and parameters[2].valueAsText:
            parameters[3].enabled = True
            bit_keys = self.get_bit_keys(parameters[2].value,
                                         parameters[1].value,
                                         bit_flags)
            parameters[3].filter.list = bit_keys

        else:
            parameters[3].enabled = False

        return

    def updateMessages(self, parameters):
        """
        Modify messages created by internal validation for each parameter.

        :param parameters:
        :return:
        """
        return

    def execute(self, parameters, messages):
        """
        Call qa_decode function to build attribute table.

        :param parameters: <list> Input parameters
        :param messages:
        :return:
        """
        def parse_valstr(input_str):
            """
            Parse semicolon delimited string into a list, and sanitize.

            :param input_str: <str>
            :return:
            """
            # split by semicolon
            val_list = input_str.split(';')

            # remove redundant quotes from each element, if applicable
            val_list_noq = [v.replace("'", "") for v in val_list]

            return val_list_noq

        in_raster = parameters[0].valueAsText
        sensor = self.get_sensor(parameters[1].valueAsText)
        band = parameters[2].valueAsText
        qa_layers = parse_valstr(parameters[3].valueAsText)
        basename = parameters[5].valueAsText
        combine = parameters[4].valueAsText

        extract_bands.extract_bits_from_band(in_raster, sensor, band,
                                             qa_layers, basename,
                                             combine_layers=combine)
