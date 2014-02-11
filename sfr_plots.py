# program to plot SFR segment profiles

import os
import numpy as np
import discomb_utilities as disutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from collections import defaultdict
import arcpy
import SFR_arcpy




class plot_elevation_profiles:
    # takes information from classes in SFR_classes.py and formats for plotting
    def __init__(self, SFRdata, COMIDdata):
        self.segs2plot = sorted(COMIDdata.allcomids.keys())[::20]
        self.SFRdata = SFRdata
        self.elevs_by_cellnum = dict()
        self.seg_dist_dict = dict()
        self.seg_elev_fromNHD_dict = dict()
        self.seg_elev_fromContours_dict = dict()
        self.seg_elev_fromDEM_dict = dict()
        self.L1top_elev_dict = dict()
        self.profiles = [self.L1top_elev_dict, self.seg_elev_fromNHD_dict, self.seg_elev_fromContours_dict, self.seg_elev_fromDEM_dict]
        self.profile_names = ['model top', 'NHDPlus', 'topographic contours',
                               'DEM']


    def read_DIS(self):
        DX, DY, NLAY, NROW, NCOL, i = disutil.read_meta_data(self.SFRdata.MFdis)

        # get layer tops/bottoms
        self.layer_elevs = np.zeros((NLAY+1, NROW, NCOL))
        for c in range(NLAY + 1):
            tmp, i = disutil.read_nrow_ncol_vals(self.SFRdata.MFdis, NROW, NCOL, 'float', i)
            self.layer_elevs[c, :, :] = tmp

        # make dictionary of model top elevations by cellnum
        for c in range(NCOL):
            for r in range(NROW):
                cellnum = r*NCOL + c + 1
                self.elevs_by_cellnum[cellnum] = self.layer_elevs[0, r, c]


    def get_comid_plotting_info(self, FragIDdata):

        for seg in self.segs2plot:
            distances = []
            elevs_fromNHD = []
            elevs_fromContours = []
            elevs_fromDEM = []
            L1top_top_elevs = []
            dist = 0
            for fid in FragIDdata.COMID_orderedFragID[seg]:
                dist += FragIDdata.allFragIDs[fid].lengthft
                distances.append(dist)
                mean_elev_fromNHD = 0.5 * (FragIDdata.allFragIDs[fid].NHDPlus_elev_max + FragIDdata.allFragIDs[fid].NHDPlus_elev_min)
                mean_elev_fromContours = 0.5 * (FragIDdata.allFragIDs[fid].interpolated_contour_elev_max + FragIDdata.allFragIDs[fid].interpolated_contour_elev_min)
                mean_elev_fromDEM = 0.5 * (FragIDdata.allFragIDs[fid].smoothed_DEM_elev_max + FragIDdata.allFragIDs[fid].smoothed_DEM_elev_min)
                elevs_fromNHD.append(mean_elev_fromNHD)
                elevs_fromContours.append(mean_elev_fromContours)
                elevs_fromDEM.append(mean_elev_fromDEM)
                cellnum = FragIDdata.allFragIDs[fid].cellnum
                L1top_top_elevs.append(self.elevs_by_cellnum[cellnum])

            self.seg_dist_dict[seg] = distances
            self.seg_elev_fromNHD_dict[seg] = elevs_fromNHD
            self.seg_elev_fromContours_dict[seg] = elevs_fromContours
            self.seg_elev_fromDEM_dict[seg] = elevs_fromDEM
            self.L1top_elev_dict[seg] = L1top_top_elevs



    def plot_profiles(self, pdffile, **kwargs):

        # segs2plot= list of segments to plot
        # seg_distdict= list of distances along segments
        # profiles= list of dictionaries containing profiles for each segment
        # profilenames= list of names, one for each type of profile e.g., model top, STOP post-fix_w_DEM, etc.
        # pdffile= name for output pdf

        try:
            Bottomsdict = kwargs['Bottoms']
            Bottoms = True
        except KeyError:
            Bottoms = False
        try:
            plot_slopes = kwargs['plot_slopes']
            Slopesdict = kwargs['slopes']
            Reach_lengthsdict = kwargs['reach_lengths']
        except KeyError:
            plot_slopes = False

        # function to reshape distances and elevations to plot actual cell elevations
        def reshape_seglist(seg_dict, distance):
            if distance:
                seg_list = [0]
            else:
                seg_list = []
            for i in range(len(seg_dict)):
                seg_list.append(seg_dict[i])
                seg_list.append(seg_dict[i])
            if distance:
                seg_list = seg_list[:-1] # trim last, since last seg distances denotes end of last reach
            return seg_list

        pdf = PdfPages(pdffile)
        print "\nsaving plots of selected COMIDs to " + pdffile
        knt = 0
        for seg in self.segs2plot:
            knt += 1
            print "\rCOMID: {0} ({1} of {2})".format(seg, knt, len(self.segs2plot)),
            # reshape distances and elevations to plot actual cell elevations
            seg_distances = reshape_seglist(self.seg_dist_dict[seg], True)
            profiles2plot = []
            for i in range(len(self.profiles)):
                profile = reshape_seglist(self.profiles[i][seg], False)
                profiles2plot.append(profile)

            if Bottoms:
                seg_Bots = reshape_seglist(Bottomsdict[seg], False)
                profiles2plot.append(seg_Bots)
                self.profile_names.append('model bottom')

            if plot_slopes:
                slopes = reshape_seglist(Slopesdict[seg], False)
                reachlengths = reshape_seglist(Reach_lengthsdict[seg], False)


            fig = plt.figure()
            if plot_slopes:
                ((ax1, ax2)) = fig.add_subplot(2, 1, sharex=True, sharey=False)
            else:
                ax1 = fig.add_subplot(1, 1, 1)
            ax1.grid(True)
            colors = ['b', 'g', 'r', 'k']

            for i in range(len(profiles2plot)):
                ax1.plot(seg_distances, profiles2plot[i], color=colors[i], label=self.profile_names[i])

            handles, labels = ax1.get_legend_handles_labels()
            ax1.legend(handles, labels, loc='best')
            ax1.set_title('Streambed profile for COMID ' + str(seg))
            plt.xlabel('distance along COMID (ft.)')
            ax1.set_ylabel('Elevation (ft)')

            # adjust limits to make all profiles visible
            ymax, ymin = np.max(profiles2plot), np.min(profiles2plot)
            ax1.set_ylim([ymin-10, ymax+10])

            # plot segment slopes if desired
            if plot_slopes:
                ax2.grid(True)
                ax2.plot(seg_distances, slopes, color='0.75', label='streambed slopes')
                ax2.set_ylabel('Streambed slope')
                ax3 = ax2.twinx()
                ax3.plot(self.seg_dist_dict[seg], reachlengths, 'b', label='reach length')
                ax3.set_ylabel('reach length (ft)')
                handles, labels = ax2.get_legend_handles_labels()
                ax2.legend(handles, labels, fontsize=6)
                ax3.legend(loc=0)
            pdf.savefig(fig)
        pdf.close()
        plt.close('all')


class plot_streamflows:
    # plots simulated flows over the SFR network
    def __init__(self, DISfile, streams_shp, SFR_out):
        self.streams_shp = streams_shp
        self.SFR_out = SFR_out
        self.flow_by_cellnum = dict()
        self.seg_rch_by_cellnum = dict()
        self.DISfile = DISfile
        self.outpath = os.path.split(SFR_out)[0]
        if len(self.outpath) == 0:
            self.outpath = os.getcwd()

    def join_SFR_out2streams(self):

        # get model info
        try:
            DX, DY, NLAY, NROW, NCOL, i = disutil.read_meta_data(self.DISfile)
        except:
            raise IOError("Cannot read MODFLOW DIS file {0}".format(self.DISfile))

        print "aggregating flow information by cellnum..."
        indata = np.genfromtxt(self.SFR_out, skiprows=8, dtype=None)
        for line in indata:
            r, c = line[1], line[2]
            seg_rch = "{0} {1}; ".format(line[3], line[4])
            flow = 0.5 * (line[5] + line[7])
            cellnum = (r-1)*NCOL + c

            try:
                existingflow = self.flow_by_cellnum[cellnum]
                seg_rch_info = self.seg_rch_by_cellnum[cellnum]
            except KeyError:
                existingflow = 0
                seg_rch_info = 'segs  rchs: '

            self.flow_by_cellnum[cellnum] = existingflow + flow
            self.seg_rch_by_cellnum[cellnum] = seg_rch_info + seg_rch

        # write to temporary output file
        ofp = open('temp.csv','w')
        ofp.write('cellnum,row,column,seg_reach,flow\n')
        for cn in self.flow_by_cellnum.keys():
            ofp.write('{0},{1},{2},"{3}",{4:.6e}\n'.format(cn, 1, 1, self.seg_rch_by_cellnum[cn], self.flow_by_cellnum[cn]))
        ofp.close()

        # make feature/table layers
        arcpy.env.workspace = self.outpath
        arcpy.env.overwriteOutput = True
        arcpy.CopyFeatures_management(self.streams_shp, self.streams_shp[:-4]+'_backup.shp')
        arcpy.MakeFeatureLayer_management(self.streams_shp[:-4]+'_backup.shp', "streams")
        arcpy.CopyRows_management('temp.csv', os.path.join(self.outpath, 'temp.dbf'))


        # drop all fields except for cellnum from stream linework
        Fields = arcpy.ListFields("streams")
        Fields = [f.name for f in Fields if f.name not in ["FID", "Shape", "cellnum"]]
        arcpy.DeleteField_management("streams", Fields)

        outfile = os.path.join(self.outpath, "{0}.shp".format(self.SFR_out[:-4]))
        SFR_arcpy.general_join(outfile, "streams", "cellnum", "temp.dbf", "cellnum", keep_common=True)