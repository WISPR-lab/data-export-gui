# Device HIN (Heterogeneous Information Network) Graph Analysis.
#
# This module clusters raw telemetry records (events and devices_raw) and their computed linkage edges
# (deduplication, static IDs, and version upgrades) using a Union-Find algorithm.
#
# The resulting connected components serve as heuristic groupings (represented by DeviceInstance objects).
# These represent a best-effort attempt to aggregate events associated with the same logical device instance,
# though they may over-merge or under-merge records depending on the confidence of the computed edges.
#
# A Device Profile (calculated via calculate_profile_updates) is a static model/manufacturer classification
# bucket that groups multiple Device Instances sharing the exact manufacturer and model name.
#
# Chronological order is maintained by sorting the DataFrame by 'timestamp' during initialization.
# Lists extracted via unique() natively return values sorted chronologically by occurrence.
#
# Relationship Hierarchy:
#
#                       [ Device Profile ]
#                     "Apple iPhone 13 Pro"
#              (General Model/Manufacturer Category)
#                       /                \
#                      /                  \
#          [ Device Instance A ]        [ Device Instance B ]
#             (Client: Google)             (Client: Facebook)
#              /          \                 /          \
#             /            \               /            \
#        [Event 1]      [Event 2]     [Event 3]      [Event 4]
#         Time: T1       Time: T2      Time: T3       Time: T4
#        OS: 15.0       OS: 15.1      OS: 16.0       OS: 16.1

import json
import uuid
import pandas as pd
from datetime import datetime, timezone
from typing import List, Optional


class DeviceInstance:
    # Abstractly, this represents a represents a single logical device sequence over time. 
    # It is our best-effort reconstruction of a single physical device's timeline based on the computed database linkages.
    # 
    # Concretely, it  wraps a Pandas  DataFrame  containing the subset of events and raw device rows 
    # associated with that cluster and calculates aggregations over it that the DB can reference.
    def __init__(self, root_id: str, df: pd.DataFrame):
        self.root_id = root_id
        self.df = df.sort_values(by='timestamp') 
        
        first_row = self.df.iloc[0]
        self.upload_id = first_row.get('upload_id')
        self.platform = first_row.get('platform')

        self.manufacturer = self._find_best_attribute('attr__norm__manufacturer')
        self.model = self._find_best_attribute('attr__norm__model_name')
        self.client_name = self._find_best_attribute('attr__norm__client_name')
        self.os_name = self._find_best_attribute('attr__norm__os_name')
        self.os_type = self._find_best_attribute('attr__norm__os_type')

        self.apple_masking = self._evaluate_apple_masking()

        valid_ts = self.df['timestamp'].dropna()
        if not valid_ts.empty:
            min_ts = valid_ts.min()
            max_ts = valid_ts.max()
            self.first_seen = float(min_ts.timestamp()) if hasattr(min_ts, 'timestamp') else float(min_ts)
            self.last_seen = float(max_ts.timestamp()) if hasattr(max_ts, 'timestamp') else float(max_ts)
        else:
            self.first_seen = None
            self.last_seen = None

        self.event_count = int(len(self.df[self.df['table'] == 'events']))

        self.os_versions = self.df['attr__norm__os_version'].dropna().unique().tolist() if 'attr__norm__os_version' in self.df.columns else []
        self.client_versions = self.df['attr__norm__client_version'].dropna().unique().tolist() if 'attr__norm__client_version' in self.df.columns else []
        self.client_ips = self.df['attr__client_ip'].dropna().unique().tolist() if 'attr__client_ip' in self.df.columns else []
        self.locations = self.df['attr__location'].dropna().unique().tolist() if 'attr__location' in self.df.columns else []

    def _find_best_attribute(self, col: str) -> Optional[str]:
        # Retains the most specific attribute value (e.g. choosing 'iPhone 13' over a generic 'iPhone' when merged).
        if col not in self.df.columns:
            return None
        non_nulls = self.df[col].dropna().unique()
        if len(non_nulls) == 0:
            return None
        return sorted(non_nulls, key=lambda s: len(str(s)), reverse=True)[0]

    def _evaluate_apple_masking(self) -> Optional[int]:
        # Apple's Safari browser intentionally masks device hardware details within the User Agent string
        # to prevent browser fingerprint tracking (e.g. reporting a generic 'Macintosh' with no specific macOS 
        # version or 'iPhone' with no specific model version). This function flags instances where this privacy 
        # masking is occurring to inform downstream clustering.
        os_val = (self._find_best_attribute('attr__norm__os_name') or '').strip().lower()
        client_val = (self._find_best_attribute('attr__norm__client_name') or '').strip().lower()
        model_val = (self._find_best_attribute('attr__norm__model_name') or '').strip().lower()

        # Ensure this won't apply to webkit
        if 'webkit' in client_val:
            return None

        # Check if the device model is generic
        is_generic_mac = (os_val == 'macos' and model_val == 'macintosh')
        is_generic_ios = (os_val in ('ios', 'iphone os') and model_val in ('iphone', 'ipad', 'ipod'))

        if not (is_generic_mac or is_generic_ios):
            return None

        # Check if the OS string is frozen (specifically for macOS 10.15)
        if is_generic_mac:
            os_versions = self.df['attr__norm__os_version'].dropna().unique().tolist() if 'attr__norm__os_version' in self.df.columns else []
            has_frozen_mac_os = any(str(ver).startswith('10.15') for ver in os_versions)
            if not has_frozen_mac_os:
                return None

        return 1

    def export_as_dict(self) -> dict:
        # Serializes the instance data into a flat database-compatible dictionary, retrieving the latest versions/IPs 
        # by selecting the last elements of the chronologically-sorted telemetry arrays.
        return {
            'id': self.root_id,
            'upload_id': self.upload_id,
            'platform': self.platform,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'client_name': self.client_name,
            'os_name': self.os_name,
            'os_type': self.os_type,
            'apple_masking': self.apple_masking,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
            'last_seen_dt': datetime.fromtimestamp(self.last_seen, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S Z') if self.last_seen else None,
            'event_count': self.event_count,
            'latest_os_version': self.os_versions[-1] if self.os_versions else None,
            'latest_client_version': self.client_versions[-1] if self.client_versions else None,
            'latest_client_ip': self.client_ips[-1] if self.client_ips else None,
            'os_versions': self.os_versions,
            'client_versions': self.client_versions,
            'client_ips': self.client_ips,
            'locations': self.locations
        }


 
class DeviceInstanceGraph:
    # This is really just a memory utility class that takes the raw vertices and edges tables and actually computes
    # the subgraphs, which are the Device "instances" as seen before. 
    # The main algorithmic work happens in get_instances(), which runs a connected components algorithm (via Union-Find).
    def __init__(self, vertices_df: pd.DataFrame, edges_df: pd.DataFrame):
        self.vertices_df = self.vertices_df = vertices_df.copy()
        self.edges_df = edges_df.copy()
        self._parent = {vid: vid for vid in self.vertices_df['id']}

    def _find(self, x: str) -> str:
        if self._parent[x] != x:
            self._parent[x] = self._find(self._parent[x])
        return self._parent[x]

    def _union(self, x: str, y: str):
        root_x = self._find(x)
        root_y = self._find(y)
        if root_x != root_y:
            self._parent[root_x] = root_y

    def get_instances(self) -> List[DeviceInstance]:
        # Runs a connected components algorithm to merge event and device records into subgraphs based on the 
        # linkages we created (deterministic hardware/session IDs, metadata deduplication, and client/OS upgrades).
        # The result is a list of DeviceInstance containers, each holding its respective rows.
        for vid in self._parent:
            self._parent[vid] = vid

        linkage_types = {'Hardware', 'PlatformFingerprint', 'Session', 'ClientUpgrade', 'OSUpgrade', 'Deduplication'}
        if not self.edges_df.empty and 'type' in self.edges_df.columns:
            edges_to_process = self.edges_df[self.edges_df['type'].isin(linkage_types)]
            for _, edge in edges_to_process.iterrows():
                id_a, id_b = edge['id_a'], edge['id_b']
                if id_a in self._parent and id_b in self._parent:
                    self._union(id_a, id_b)

        root_map = {vid: self._find(vid) for vid in self._parent}
        self.vertices_df['component_root'] = self.vertices_df['id'].map(root_map)

        instances = []
        for root_id, group_df in self.vertices_df.groupby('component_root'):
            instances.append(DeviceInstance(root_id, group_df))
            
        return instances

    @staticmethod
    def format_initial(events_df: pd.DataFrame, devices_df: pd.DataFrame) -> pd.DataFrame:
        # Combines raw events and devices_raw tables, parses the JSON string 'attributes' column, and normalizes
        # nested keys into flat columns prefixed with 'attr__' to keep telemetry attributes namespaced.
        if events_df.empty:
            events_df = pd.DataFrame(columns=['id', 'upload_id', 'attributes', 'origin', 'timestamp'])
        events_df['table'] = 'events'
        events_df['timestamp'] = pd.to_datetime(events_df['timestamp'], unit='ms', errors='coerce')
        
        if devices_df.empty:
            devices_df = pd.DataFrame(columns=['id', 'upload_id', 'attributes', 'origin'])
        devices_df['table'] = 'devices_raw'
        
        df = pd.concat([devices_df, events_df], ignore_index=True)
        if df.empty:
            return pd.DataFrame(columns=['id', 'upload_id', 'origin', 'table'])
            
        parsed_json = df['attributes'].apply(lambda x: json.loads(x) if (isinstance(x, str) and x) else (x if isinstance(x, dict) else {}))
        return df.drop(columns=['attributes']).join(
            pd.json_normalize(parsed_json).add_prefix('attr__')
        )
