""" Module for managing computation of system level metrics. """
import copy

import opendssdirect as dss
import networkx as nx

from emerge.metrics.time_series_metrics import observer
from emerge.metrics import powerflow_metrics_opendss
from emerge.utils import dss_util
from emerge.metrics import data_model
from emerge.metrics import feeder_metrics_opendss
import pandas as pd

class SARDI_aggregated(observer.MetricObserver):
    """ Class for computing SARDI aggregated metric.
    
    Attributes:
        loading_limit (ThermalLoadingLimit): Instance of `ThermalLoadingLimit` 
            data model.
        sardi_transformer (float): SARDI_line metric
        counter (int): Counter for keeping track how number
            of times compute function is called
        network (nx.Graph): Networkx graph representing
            distribution network
    """


    def __init__(self, 
        loading_limit: float = 1.0,
        voltage_limit: dict = {
            'overvoltage_threshold': 1.05,
            'undervoltage_threshold': 0.95
            }
        ):
        """ Constructor for `SARDI_line` class. 
        
        Args:
            loading_limit (float): Per unit loading limit
                used for computing SARDI_line metric.
            voltage_limit (dict): Voltage threshold
        """

        self.loading_limit = data_model.ThermalLoadingLimit(threshold=loading_limit)
        self.voltage_limit = data_model.VoltageViolationLimit(**voltage_limit)
        self.sardi_aggregated = 0
        self.counter = 0
    
    def _get_initial_dataset(self, dss_instance: dss):
        
        """ Get initial dataset for computing the metric. """
        self.network = feeder_metrics_opendss.networkx_from_opendss_model(dss_instance)
        self.load_bus_map = dss_util.get_bus_load_dataframe(dss_instance)
        self.substation_bus = dss_util.get_source_node(dss_instance)
        self.bus_load_flag_df = dss_util.get_bus_load_flag(dss_instance)

    def compute(self, dss_instance:dss):
        """ Refer to base class for more details. """

        # Get line loading dataframe
        transformer_loading_df = powerflow_metrics_opendss.get_transloading_dataframe(dss_instance)
        line_loading_df = powerflow_metrics_opendss.get_lineloading_dataframe(dss_instance)
        voltage_df = powerflow_metrics_opendss.get_voltage_dataframe(dss_instance)
        
        if not self.counter:
            self._get_initial_dataset(dss_instance)

        v_filter = voltage_df.loc[self.load_bus_map["busname"]].drop_duplicates()
        ov_flags = v_filter['voltage(pu)']>self.voltage_limit.overvoltage_threshold
        uv_flags = v_filter['voltage(pu)']<self.voltage_limit.undervoltage_threshold
        overvoltage_v = v_filter[ov_flags]
        undervoltage_v = v_filter[uv_flags]
        merged_load_buses = set(pd.concat([overvoltage_v, undervoltage_v]).index)
        
        self.network_copy = copy.deepcopy(self.network)
        overloaded_trans = transformer_loading_df[transformer_loading_df['loading(pu)']> self.loading_limit.threshold]
        overloaded_lines = line_loading_df[line_loading_df['loading(pu)']> self.loading_limit.threshold]

        if not all([overloaded_trans.empty, overloaded_lines.empty]) :
            
            xfmrs = [] if overloaded_trans.empty else list(overloaded_trans.index)
            lines = [] if overloaded_lines.empty else list(overloaded_lines.index)

            edge_segments = xfmrs + lines
            edge_to_be_removed = []
            
            for edge in self.network_copy.edges():
                edge_data = self.network_copy.get_edge_data(*edge)
                if edge_data and 'name' in edge_data and edge_data['name'] in edge_segments:
                    edge_to_be_removed.append(edge)

            self.network_copy.remove_edges_from(edge_to_be_removed)
            connected_buses = nx.node_connected_component(self.network_copy, self.substation_bus)
            impacted_buses = self.bus_load_flag_df.loc[self.bus_load_flag_df.index.difference(connected_buses)]
            impacted_load_buses = set(impacted_buses[impacted_buses['is_load']==1].index)
            total_impacted_load_buses = impacted_load_buses.union(merged_load_buses)

        else:
            total_impacted_load_buses = merged_load_buses
        
        total_load = dss_instance.Loads.Count()
        self.sardi_aggregated += len(total_impacted_load_buses)*100/total_load

        self.counter +=1

    def get_metric(self):
        """ Refer to base class for more details. """
        return {
            "sardi_aggregated": self.sardi_aggregated/self.counter if self.counter >0 else 0
        }


class SARDI_transformer(observer.MetricObserver):
    """ Class for computing SARDI transformer metric.
    
    Attributes:
        loading_limit (ThermalLoadingLimit): Instance of `ThermalLoadingLimit` 
            data model.
        sardi_transformer (float): SARDI_line metric
        counter (int): Counter for keeping track how number
            of times compute function is called
        network (nx.Graph): Networkx graph representing
            distribution network
    """


    def __init__(self, 
        loading_limit: float = 1.0):
        """ Constructor for `SARDI_line` class. 
        
        Args:
            loading_limit (float): Per unit loading limit
                used for computing SARDI_line metric.
        """

        self.loading_limit = data_model.ThermalLoadingLimit(threshold=loading_limit)
        self.sardi_transformer = 0
        self.counter = 0
    
    def _get_initial_dataset(self, dss_instance: dss):
        
        """ Get initial dataset for computing the metric. """
        self.network = feeder_metrics_opendss.networkx_from_opendss_model(dss_instance)
        self.substation_bus = dss_util.get_source_node(dss_instance)
        self.bus_load_flag_df = dss_util.get_bus_load_flag(dss_instance)

    def compute(self, dss_instance:dss):
        """ Refer to base class for more details. """

        # Get line loading dataframe
        transformer_loading_df = powerflow_metrics_opendss.get_transloading_dataframe(dss_instance)
        
        if not self.counter:
            self._get_initial_dataset(dss_instance)
        
        self.network_copy = copy.deepcopy(self.network)
        overloaded_trans = transformer_loading_df[transformer_loading_df['loading(pu)']> self.loading_limit.threshold]
        
        if not overloaded_trans.empty:
            xfmrs = list(overloaded_trans.index)
            edge_to_be_removed = []
            
            for edge in self.network_copy.edges():
                edge_data = self.network_copy.get_edge_data(*edge)
                if edge_data and 'name' in edge_data and edge_data['name'] in xfmrs:
                    edge_to_be_removed.append(edge)

            self.network_copy.remove_edges_from(edge_to_be_removed)
            connected_buses = nx.node_connected_component(self.network_copy, self.substation_bus)
            filtered_bus_df = self.bus_load_flag_df.loc[connected_buses]
            total_load = dss_instance.Loads.Count()
            self.sardi_transformer += (total_load - filtered_bus_df.sum()['is_load'])*100/total_load

        self.counter +=1

    def get_metric(self):
        """ Refer to base class for more details. """
        return {
            "sardi_transformer": self.sardi_transformer/self.counter if self.counter >0 else 0
        }


class SARDI_line(observer.MetricObserver):
    """ Class for computing SARDI line metric.
    
    Attributes:
        loading_limit (ThermalLoadingLimit): Instance of `ThermalLoadingLimit` 
            data model.
        sardi_line (float): SARDI_line metric
        counter (int): Counter for keeping track how number
            of times compute function is called
        network (nx.Graph): Networkx graph representing
            distribution network
    """


    def __init__(self, 
        loading_limit: float = 1.0):
        """ Constructor for `SARDI_line` class. 
        
        Args:
            loading_limit (float): Per unit loading limit
                used for computing SARDI_line metric.
        """

        self.loading_limit = data_model.ThermalLoadingLimit(threshold=loading_limit)
        self.sardi_line = 0
        self.counter = 0
    
    def _get_initial_dataset(self, dss_instance: dss):
        
        """ Get initial dataset for computing the metric. """
        self.network = feeder_metrics_opendss.networkx_from_opendss_model(dss_instance)
        self.substation_bus = dss_util.get_source_node(dss_instance)
        self.bus_load_flag_df = dss_util.get_bus_load_flag(dss_instance)

    def compute(self, dss_instance:dss):
        """ Refer to base class for more details. """

        # Get line loading dataframe
        line_loading_df = powerflow_metrics_opendss.get_lineloading_dataframe(dss_instance)
        
        if not self.counter:
            self._get_initial_dataset(dss_instance)
        
        self.network_copy = copy.deepcopy(self.network)
        overloaded_lines = line_loading_df[line_loading_df['loading(pu)']> self.loading_limit.threshold]
        
        if not overloaded_lines.empty:
            line_segments = list(overloaded_lines.index)
            edge_to_be_removed = []
            
            for edge in self.network_copy.edges():
                edge_data = self.network_copy.get_edge_data(*edge)
                if edge_data and 'name' in edge_data and edge_data['name'] in line_segments:
                    edge_to_be_removed.append(edge)

            self.network_copy.remove_edges_from(edge_to_be_removed)
            connected_buses = nx.node_connected_component(self.network_copy, self.substation_bus)
            filtered_bus_df = self.bus_load_flag_df.loc[list(connected_buses)]
            total_load = dss_instance.Loads.Count()
            self.sardi_line += (total_load - filtered_bus_df.sum()['is_load'])*100/total_load

        self.counter +=1

    def get_metric(self):
        """ Refer to base class for more details. """
        return {
            "sardi_line": self.sardi_line/self.counter if self.counter >0 else 0
        }


class SARDI_voltage(observer.MetricObserver):
    """ Class for managing the computation of SARDI voltage metric.
    
    Attributes:
        upper_threshold (float): Voltage upper threshold
        lower_threshold (float): Voltage lower threshold
        sardi_voltage (float): SARDI voltage metric
        counter (int): Counter for keeping track how number
            of times compute function is called
        load_bus_map (pd.DataFrame): Dataframe containing mapping
            between bus and load
    """

    def __init__(
        self,
        upper_threshold: float = 1.05,
        lower_threshold: float = 0.95
    ):
        """ Constructor for SARDI_voltage metric.
        
        Args:
            upper_threshold (float): Voltage upper threshold
            lower_threshold (float): Voltage lower threshold
        """
        
        self.upper = upper_threshold
        self.lower = lower_threshold
        self.sardi_voltage = 0
        self.counter = 0

    def compute(self, dss_instance:dss):
        """ Refer to base class for more details. """

        # Get voltage dataframe and load bus mapper
        voltage_df = powerflow_metrics_opendss.get_voltage_dataframe(dss_instance)
        
        if not hasattr(self, 'load_bus_map'):
            self.load_bus_map = dss_util.get_bus_load_dataframe(dss_instance)
        
        # Filter voltages for load buses only 
        # and count the number of overvoltages and undervoltages
        v_filter = voltage_df.loc[self.load_bus_map["busname"]].drop_duplicates()
        overvoltage_count = v_filter[v_filter['voltage(pu)']>self.upper].count()['voltage(pu)']
        undervoltage_count = v_filter[v_filter['voltage(pu)']<self.lower].count()['voltage(pu)']

        self.sardi_voltage += (overvoltage_count + undervoltage_count)*100/len(self.load_bus_map)
        self.counter +=1

    def get_metric(self):
        """ Refer to base class for more details. """
        return {
            "sardi_voltage": self.sardi_voltage/self.counter if self.counter >0 else 0
        }


