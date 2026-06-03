import pandas as pd
from typing import List
from .level2 import compare_versions

class DeviceInstance:
    def __init__(self, root_id: str, df: pd.DataFrame):
        self.root_id = root_id
        # df contains the subset of rows (vertices) for this instance, sorted chronologically
        self.df = df.sort_values(by='timestamp') 

    def resolve_consensus_attributes(self) -> dict:
        """
        Finds the consensus of normalized attributes using fast backfill/forwardfill
        on the DataFrame slice.
        """
        norm_cols = [c for c in self.df.columns if c.startswith('attr__norm__')]
        if not norm_cols or self.df.empty:
            return {}
        
        # Take the first non-null value for each column across all rows
        filled = self.df[norm_cols].bfill().ffill()
        if filled.empty:
            return {}
        consensus_series = filled.iloc[0]
        return consensus_series.dropna().to_dict()

    def get_timeline(self) -> List[tuple]:
        """Returns sorted list of (timestamp, OS_version) tuples."""
        # Find the OS version column name
        os_col = 'attr__norm__os_version'
        if os_col not in self.df.columns:
            return []
        subset = self.df[['timestamp', os_col]].dropna()
        return list(subset.itertuples(index=False, name=None))

    def is_os_monotonic_with(self, other: 'DeviceInstance') -> bool:
        """Concatenates timelines and checks OS version monotonicity."""
        timeline_self = self.get_timeline()
        timeline_other = other.get_timeline()
        if not timeline_self or not timeline_other:
            return True

        combined = sorted(timeline_self + timeline_other, key=lambda x: x[0])
        last_version = None
        for timestamp, os_ver in combined:
            if not os_ver:
                continue
            if last_version:
                if compare_versions(os_ver, last_version) == 'LT':
                    return False
            last_version = os_ver
        return True


class DeviceHINGraph:
    def __init__(self, vertices_df: pd.DataFrame, edges_df: pd.DataFrame):
        self.vertices_df = vertices_df.copy()
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
        """Groups vertices into DeviceInstance components using Union-Find on Phase 1 edges."""
        # Reset parent mappings
        for vid in self._parent:
            self._parent[vid] = vid

        # Filter Phase 1 edges (exclude DeviceModel)
        phase1_types = {'Hardware', 'PlatformFingerprint', 'Session', 'ClientUpgrade', 'OSUpgrade', 'Deduplication'}
        if not self.edges_df.empty and 'type' in self.edges_df.columns:
            edges_to_process = self.edges_df[self.edges_df['type'].isin(phase1_types)]
            for _, edge in edges_to_process.iterrows():
                id_a, id_b = edge['id_a'], edge['id_b']
                if id_a in self._parent and id_b in self._parent:
                    self._union(id_a, id_b)

        # Assign component root back to vertices
        self.vertices_df['component_root'] = self.vertices_df['id'].apply(self._find)

        # Group by root and build DeviceInstance objects
        instances = []
        for root_id, group_df in self.vertices_df.groupby('component_root'):
            instances.append(DeviceInstance(root_id, group_df))
            
        return instances
