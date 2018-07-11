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
1.2     21 Aug 2017     Added ability to unpack bits to individual files.
"""
import arcpy
import qa_decode


class DecodeQA(object):
    def __init__(self):
        """
        Define the tool (tool name is the name of the class).
        """
        self.label = "Decode QA"
        self.description = ""
        self.params = arcpy.GetParameterInfo()
        self.canRunInBackground = False

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
                              'radsat_qa',
                              'sr_aerosol',
                              'sr_cloud_qa']

        # Fourth parameter (keep or remove low)
        param3 = arcpy.Parameter(
            displayName="Remove low labels",
            name="rm_low",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        params = [param0, param1, param2, param3]
        return params

    def updateParameters(self, parameters):
        """
        Set default values in Arc Toolbox interface based on input band.

        :param parameters: <list> Input parameters
        :return:
        """
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
        raster = parameters[0].valueAsText
        sensor = parameters[1].valueAsText
        band = parameters[2].valueAsText
        rm_low = parameters[3].valueAsText

        qa_decode.build_attr_table(raster, sensor, band, rm_low)
