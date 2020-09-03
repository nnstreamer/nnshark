import argparse
import os
import plotly.graph_objects as go
import copy
import numpy as np
from plotly.subplots import make_subplots

logging_period = 0.1
cpu_num = 8

ts = 0

cpu_data = []
element_data = {}
pad_data = {}
element_name = []

buffer_timeline_y = []
buffer_timeline_data = {}

def parse_log_file():
    metadata_file = args.dir + "/log_metadata"
    log_file = args.dir + "/log"

    with open(metadata_file, "r") as f:
        for i in f.readlines():
            if len(i.split(" ")) > 1:
                element_name.append(i.split(" ")[1].split("\n")[0])
            else:
                ts = float(i)

    for i in range(cpu_num):
        cpu_data.append([])
    
    prev_cpuusage = np.zeros(cpu_num)
    prev_proctime = np.zeros(len(element_name))
    prev_queuelevel = np.zeros(len(element_name))
    prev_maxqueue = np.zeros(len(element_name))
    prev_bufrate = np.zeros(len(element_name))

    for i in range(len(element_name)):
        # Add -1 for Enable value (element don't need bufrate)
        if(len(element_name[i].split("-")) == 1):
            element_data[i] = {"proctime" : [], "queuelevel" : [], "maxqueue" : []}
            prev_bufrate[i] = -1
        else:
            pad_data[i] = {"bufrate" : []}
            prev_proctime[i] = -1
            prev_queuelevel[i] = -1
            prev_maxqueue[i] = -1
    
    with open(log_file, "r") as f:
        data = f.readlines()
        idx = 0
        # Parse Initial data
        while(data[idx].split("\n")[0] == "t"):
            ts += logging_period
            idx += 1

        # Parsing remain data
        for i in range(idx, len(data)):
            parsed_data = data[i].split("\n")[0].split(" ")

            # Next data
            if(parsed_data[0] == "t"):
                for i in range(cpu_num):
                    cpu_data[i].append(prev_cpuusage[i])

                for i in range(len(element_name)):
                    if(prev_proctime[i] != -1):
                        element_data[i]["proctime"].append(prev_proctime[i])
                    if(prev_queuelevel[i] != -1):
                        element_data[i]["queuelevel"].append(prev_queuelevel[i])
                    if(prev_maxqueue[i] != -1):
                        element_data[i]["maxqueue"].append(prev_maxqueue[i])
                    if(prev_bufrate[i] != -1):
                        pad_data[i]["bufrate"].append(prev_bufrate[i])

            # CPU Usage data
            elif(parsed_data[0] == "c"):
                for i in range(cpu_num):
                    prev_cpuusage[i] = float(parsed_data[i+1]) / 10
            # pad data
            elif(parsed_data[0] == "p"):
                prev_bufrate[int(parsed_data[1])] += float(parsed_data[2]) / 100
            # element data
            else:
                if(parsed_data[1] != '.'):
                    prev_proctime[int(parsed_data[0])] += float(parsed_data[1])
                if(parsed_data[2] != '.'):
                    prev_queuelevel[int(parsed_data[0])] += int(parsed_data[2])
                if(parsed_data[3] != '.'):
                    prev_maxqueue[int(parsed_data[0])] += int(parsed_data[3])

        # append last data

        for i in range(cpu_num):
            cpu_data[i].append(prev_cpuusage[i])

        for i in range(len(element_name)):
            if(prev_proctime[i] != -1):
                element_data[i]["proctime"].append(prev_proctime[i])
            if(prev_queuelevel[i] != -1):
                element_data[i]["queuelevel"].append(prev_queuelevel[i])
            if(prev_maxqueue[i] != -1):
                element_data[i]["maxqueue"].append(prev_maxqueue[i])
            if(prev_bufrate[i] != -1):
                pad_data[i]["bufrate"].append(prev_bufrate[i])

def parse_log_buffer_file():
    # find buffer files
    for idx, name in enumerate(element_name):
        buffer_file_path = args.dir + "/buffer-" + name

        if(os.path.exists(buffer_file_path)):
            buffer_timeline_y.append(name)

            with open(buffer_file_path, "r") as f:
                wholeFile = f.readlines()
                for i in range(len(wholeFile)-1):
                    current_ts = float(wholeFile[i].split(" ")[0])
                    next_ts = float(wholeFile[i+1].split(" ")[0])
                    buffer_offset = wholeFile[i].split(" ")[1].split("\n")[0]

                    if not buffer_timeline_data.get(buffer_offset):
                        buffer_timeline_data[buffer_offset] = {"pad_name" : [], "base" : [], "len" : []}

                    buffer_timeline_data[buffer_offset]["pad_name"].append(name)
                    buffer_timeline_data[buffer_offset]["base"].append(round(current_ts, 4))
                    buffer_timeline_data[buffer_offset]["len"].append(round(next_ts - current_ts, 4))

def visualize():
    x = np.arange(len(cpu_data[0]))

    config = dict({'scrollZoom': True})

    ### CPU Usage Plot
    # CPU plot
    fig = make_subplots(rows=2, cols=1)
    for i in range(len(cpu_data)):
        fig.add_trace(go.Scatter(
            x=x/10,
            y=cpu_data[i],
            name = 'CPU ' + str(i),
            connectgaps=True
        ), row=1, col=1)

    # buffer timeline plot
    for buffer_idx in buffer_timeline_data:
        fig.add_trace(go.Bar(
            y=buffer_timeline_data[buffer_idx]["pad_name"],
            x=buffer_timeline_data[buffer_idx]["len"],
            base=buffer_timeline_data[buffer_idx]["base"],
            orientation='h',
            showlegend=False
        ), row=2, col=1)

    fig.update_layout(
        title="CPU Usage",
        xaxis_title="time (s)",
        yaxis_title="CPU Usage (%)",
        barmode='stack',
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="#7f7f7f"
        )
    )

    fig.update_xaxes(range=[0, len(cpu_data[0])/10], row=2, col=1)

    fig.show(config=config)

    ### Process Time Plot
    # proctime plot
    fig2 = make_subplots(rows=2, cols=1)
    for idx in element_data:
        fig2.add_trace(go.Scatter(
            x=x/10,
            y=element_data[idx]["proctime"],
            name = element_name[idx],
            connectgaps=True
        ), row=1, col=1)

    # buffer timeline plot
    for buffer_idx in buffer_timeline_data:
        fig2.add_trace(go.Bar(
            y=buffer_timeline_data[buffer_idx]["pad_name"],
            x=buffer_timeline_data[buffer_idx]["len"],
            base=buffer_timeline_data[buffer_idx]["base"],
            orientation='h',
            showlegend=False
        ), row=2, col=1)

    fig2.update_layout(
        title="proctime",
        xaxis_title="time (s)",
        yaxis_title="proctime (ns)",
        barmode='stack',
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="#7f7f7f"
        )
    )
    fig2.update_xaxes(range=[0, len(cpu_data[0])/10], row=2, col=1)

    fig2.show(config=config)

    ### Bufrate Plot
    # bufrate plot
    fig3 = make_subplots(rows=2, cols=1)
    for idx in pad_data:
        fig3.add_trace(go.Scatter(
            x=x/10,
            y=pad_data[idx]["bufrate"],
            name = element_name[idx],
            connectgaps=True
        ), row=1, col=1)

    # buffer timeline plot
    for buffer_idx in buffer_timeline_data:
        fig3.add_trace(go.Bar(
            y=buffer_timeline_data[buffer_idx]["pad_name"],
            x=buffer_timeline_data[buffer_idx]["len"],
            base=buffer_timeline_data[buffer_idx]["base"],
            orientation='h',
            showlegend=False
        ), row=2, col=1)

    fig3.update_layout(
        title="Buftate",
        xaxis_title="time (s)",
        yaxis_title="bufrate (s)",
        barmode='stack',
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="#7f7f7f"
        )
    )
    fig3.update_xaxes(range=[0, len(cpu_data[0])/10], row=2, col=1)
        
    fig3.show(config=config)


if __name__ == "__main__":
    # Parse argument
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', '-d', help='directory which have your LiveProfiler Log', required=True)
    args = parser.parse_args()

    # Check if directory exists
    if not os.path.isdir(args.dir):
        print("Invalid directory %s" % (args.dir))
        exit(1)
    
    if not os.path.isfile(args.dir + "/log"):
        print("No log file in your directory")
        exit(1)

    if not os.path.isfile(args.dir + "/log_metadata"):
        print("No log metadata file in your directory")
        exit(1)

    parse_log_file()
    parse_log_buffer_file()
    visualize()
