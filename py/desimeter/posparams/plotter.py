# -*- coding: utf-8 -*-
"""
Plot time series of positioner parameters.
"""

import os
import sys
import matplotlib.pyplot as plt
import tkinter.filedialog as filedialog
import time
import multiprocessing
import numpy as np
from astropy.table import Table
from astropy.time import Time

# DESI-specific imports
# path handling is to be improved as I migrate better into github/desimeter
desimeter_path = os.path.abspath('..')
sys.path.append(desimeter_path)
import posparams.fitter as fitter

# common options
img_ext = '.png'
max_plots = None # set to integer to limit # of plots (i.e. for debugging) or None to plot for all posids
home_dir = os.getenv('HOME')
main_dir = os.path.join(home_dir, 'Desktop/posparams')
savedir_prefix = os.path.join(main_dir, 'plots_')
tick_period_days = 7
day_in_sec = 24*60*60
n_processes_max = os.cpu_count() - 1 # max number of processors to use

# plot definitions
plot_defs= [{'keys': ['FIT_ERROR_STATIC', 'FIT_ERROR_DYNAMIC'],
             'units': 'um RMS',
             'mult': 1000,
             'subplot': 1,
             'logscale': True,
             'equal_scales': True},
            
            {'keys': ['NUM_POINTS'],
             'units': 'USED IN FIT',
             'mult': 1,
             'subplot': 4,
             'logscale': False},
            
            {'keys': ['LENGTH_R1', 'LENGTH_R2'],
             'units': 'mm',
             'mult': 1,
             'subplot': 2,
             'logscale': False,
             'equal_scales': True},
            
            {'keys': ['OFFSET_X', 'OFFSET_Y'],
             'units': 'mm',
             'mult': 1,
             'subplot': 5,
             'logscale': False,
             'equal_scales': False},
            
            {'keys': ['OFFSET_T', 'OFFSET_P'],
             'units': 'deg',
             'mult': 1,
             'subplot': 6,
             'logscale': False,
             'equal_scales': False},
            
            {'keys': ['SCALE_T', 'SCALE_P'],
             'units': '',
             'mult': 1,
             'subplot': 3,
             'logscale': False,
             'equal_scales': True},
            ]

def plot(datapath, dynamic=''):
    '''Plot best-fit positioner params data, taken from csv file.
    
    Inputs:
        datapath ... main dataset to plot, csv file path
        dynamic  ... aux file (for "dynamic" params), csv file path
    '''
    table = Table.read(datapath, format='csv')
    if dynamic:
        dynam_table = Table.read(dynamic, format='csv')
    posids = sorted(set(table['POS_ID']))
    num_posids = len(posids)
    num_plots = num_posids if max_plots == None else min(max_plots, num_posids)
    posids_to_plot = [posids[i] for i in range(num_plots)]
    basename = os.path.basename(datapath)
    timestamp = basename.split('_')[0]
    savedir = savedir_prefix + timestamp
    if not os.path.exists(savedir):
        os.makedirs(savedir)
    mp_results = {}
    with multiprocessing.Pool(processes=n_processes_max) as pool:
        for posid in posids_to_plot:
            subtable = table[table['POS_ID'] == posid]
            if dynamic:
                dynam_subtable = dynam_table[dynam_table['POS_ID'] == posid]
                some_row = dynam_subtable[0]
                statics_during_dynamic = {key:some_row[key] for key in some_row.columns if key in fitter.static_keys}
            else:
                statics_during_dynamic = {key:None for key in fitter.static_keys}
            savepath = os.path.join(savedir, posid + img_ext)
            mp_results[posid] = pool.apply_async(plot_pos, args=(subtable, savepath, statics_during_dynamic))
            print(f'Plot job added: {posid}')
        while mp_results:
            completed = set()
            for posid, result in mp_results.items():
                if result.ready():
                    completed.add(posid)
                    print(f'Plot saved: {result.get()}')
            for posid in completed:
                del mp_results[posid]
            time.sleep(0.05)

def plot_pos(table, savepath, statics_during_dynamic):
    '''Plot time series of positioner parameters, as determined by best-fit
    of historical data.
    
    Inputs:
        table ... astropy table as generated by fit_params
        savepath ... where to save output plot file
        statics_during_dynamic ... dict of static params used during the dynamic params best-fit
    '''
    posid = table['POS_ID'][0]
    plt.ioff()
    fig = plt.figure(figsize=(20,10), dpi=150)
    plt.clf()
    fig.subplots_adjust(wspace=.3, hspace=.3)
    times = Time(table['DATA_END_DATE']).unix
    tick_values = np.arange(times[0], times[-1]+day_in_sec, tick_period_days*day_in_sec)
    tick_labels = [Time(t, format='unix', out_subfmt='date').iso for t in tick_values]
    n_pts = len(table)
    marker = ''
    for p in plot_defs:
        plt.subplot(2, 3, p['subplot'])
        for key in p['keys']:
            ax_right = None
            if p['keys'].index(key) == 1:
                ax_right = plt.twinx()
                color = 'red'
                linestyle = '--'
                if n_pts == 1:
                    marker = '^'
            else:
                color = 'blue'
                linestyle = '-'
                if n_pts == 1:
                    marker = 'v'
            y = [val * p['mult'] for val in table[key]]#.tolist()]
            plt.plot(times, y, color=color, linestyle=linestyle, marker=marker)
            if not ax_right:
                ax_left = plt.gca()
            units = f' ({p["units"]})' if p['units'] else ''
            plt.ylabel(key + units, color=color)
            if p['logscale']:
                plt.yscale('log')
            if 'ylims' in p:
                plt.ylim(p['ylims'])
            if ax_right and p['equal_scales']:
                min_y = min(ax_left.get_ylim()[0], ax_right.get_ylim()[0])
                max_y = max(ax_left.get_ylim()[1], ax_right.get_ylim()[1])
                ax_left.set_ylim((min_y, max_y))
                ax_right.set_ylim((min_y, max_y))
            plt.xticks(tick_values, tick_labels, rotation=90, horizontalalignment='center', fontsize=8)
            plt.yticks(fontsize=8)
            if key == 'SCALE_P':
                s = statics_during_dynamic
                plt.text(min(plt.xlim()), min(plt.ylim()),
                         f' Using static params:\n'
                         f' LENGTH_R1 = {s["LENGTH_R1"]:>5.3f}, LENGTH_R2 = {s["LENGTH_R2"]:>5.3f}\n'
                         f' OFFSET_X = {s["OFFSET_X"]:>8.3f}, OFFSET_Y = {s["OFFSET_Y"]:>8.3f}\n'
                         f' OFFSET_T = {s["OFFSET_T"]:>8.3f}, OFFSET_P = {s["OFFSET_P"]:>8.3f}\n',
                         verticalalignment='bottom')
    analysis_date = table['ANALYSIS_DATE_DYNAMIC'][-1]
    title = f'{posid}'
    title += f'\nbest-fits to historical data'
    title += f'\nanalysis date: {analysis_date}'
    plt.suptitle(title)
    plt.savefig(savepath, bbox_inches='tight')
    plt.close(fig)
    return savepath
    
if __name__ == '__main__':
    datapath = filedialog.askopenfilename(initialdir=".",
                                          title="Select csv data file",
                                          filetypes=(("CSV","*.csv"),("all files","*.*")),
                                          )
    dynamic_path = datapath.split('merged.csv')[0] + 'dynamic.csv'
    plot(datapath, dynamic_path)

