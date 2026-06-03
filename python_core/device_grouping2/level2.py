"""
LEVEL 2 - temporal user agent version

Modification of the rule-based algo from FP-Stalker (Vastel et al., 2018).
Link: https://inria.hal.science/hal-01652021/document
Login events with user agents are subject to browser/OS versions changing over time. 
This attempts to add an edge between them.
Finally, if the platform has a separate file of logged-in devices or active sessions,
we link those. 


Pass 1 -- Browser/App upgrades
Add edge between two EVENT records, A and B, if:
(a) A is temporally before B based on timestamp 
    AND they don't differ by more than MAX_PASS_1_DAYS (60 by default)
(b) they share ALL of the following:
    - device manufacturer (e.g., Samsung, Apple)
    - device model
    - OS name (e.g., iOS, Android)
    - OS version (e.g., iOS 15.7, Android 12)
    - browser name (e.g., Chrome, Safari)
(c) AND the client/app/browser version shows a valid upgrade
    - The client version of B is >= A

Pass 2 -- OS upgrades
Add edge between two subgraphs, F and G, generated from Pass 1 if:
(a) the maximum timestamp in F is less than before the minimum timestamp in G 
    AND they don't differ by more than MAX_PASS_2_DAYS (60 by default)
(b) they share ALL of the following:
    - device manufacturer (e.g., Samsung, Apple)
    - device model
    - OS name (e.g., iOS, Android) --> *but NOT version*
    - browser name (e.g., Chrome, Safari)
(c) AND the client/app/browser version shows a valid upgrade
    - The minimum client version in G >= the maximum in F.
(d) AND the OS version shows a valid upgrade
    - The OS version of G > that of F.

"""
import pandas as pd
import re
from packaging import version

MAX_PASS_1_DAYS = 60   # sever spurious links across long time gaps
MAX_PASS_2_DAYS = 60

def _coerce_version_string(v_str: str) -> str:
    # strip non-numeric clutter from unparseable client/OS versions
    if not v_str:
        return "0.0.0"
    clean = ''.join(c for c in str(v_str) if c.isdigit() or c == '.')
    # trailing or dangling dots (e.g., '15..7' or '12.')
    clean = re.sub(r'\.+', '.', clean).strip('.')
    return clean if clean else "0.0.0"

def compare_versions(v1: str, v2: str) -> str:
    # Compares version string v1 relative to version string v2.
    # Returns 'LT', 'GT', 'EQ', or None if either is null
    if not v1 or not v2:
        return None
    if v1 == v2: return 'EQ'
    try:
        p1 = version.parse(v1)
        p2 = version.parse(v2)
    except Exception: # fallback for highly corrupted telemetry strings
        p1 = version.parse(_coerce_version_string(v1))
        p2 = version.parse(_coerce_version_string(v2))

    if p1 < p2: return 'LT'
    elif p1 > p2: return 'GT'
    else: return 'EQ'



def _pass1(events_df: pd.DataFrame, max_days = MAX_PASS_1_DAYS) -> pd.DataFrame:
    group_keys = [
        'attr__norm__manufacturer',
        'attr__norm__model_name',
        'attr__norm__os_name',
        'attr__norm__client_name'
    ]
    df = events_df.copy()
    df = df.dropna(subset=group_keys + ['timestamp'])
    df = df.sort_values(by=group_keys + ['timestamp'])

    # Essentially, we are looking for subgraphs in a big list of nodes with partitioning rules.
    # Instead of constructing each subgraph totally from the bottom up (inefficient), assume
    # we have one big graph with an edge between every adjacent entry in the sorted dataframe.
    # Then, we slowly sever edges based on the rules.

    # rule (a) - sever edges between rows that differ by more than max_days:
    exceeds_max_time = (df['timestamp'].diff().dt.days > max_days).tolist()

    # rule (b)  - sever edges between rows that don't share all the keys:
    no_id_match = df[group_keys].ne(df[group_keys].shift()).any(axis=1).tolist() # list of bools mapping to df indices

    # rule (c) - sever edges that don't follow logical version progression: 
    client_versions = df['attr__norm__client_version'].tolist()
    client_version_downgraded = [False] * len(client_versions) 
    for i in range(1, len(client_versions)):
        if no_id_match[i]:
            continue
        if compare_versions(client_versions[i - 1], client_versions[i]) == 'GT':
            client_versions[i] = True

    subgraph_boundaries = [  # combine rules
        a or b or c 
        for a, b, c in zip(exceeds_max_time, no_id_match, client_version_downgraded)
    ]
    
    # .cumsum() increments the id by 1 every time it crosses a True boundary.
    df['subgraph_id'] = pd.Series(subgraph_boundaries, index=df.index).cumsum()

    # generate all edges
    edges = df[['id', 'subgraph_id']].merge(
        df[['id', 'subgraph_id']], 
        on='subgraph_id', 
        suffixes=('_a', '_b')  # 'id_a' and 'id_b' are the node IDs
    )
    # prune
    edges = edges[edges['id_a'] < edges['id_b']][['id_a', 'id_b']].drop_duplicates() 
    edges['type'] = 'ClientUpgrade'
    edges['provenance'] = '{"upgrade_type": "Client/Browser version"}'
    return edges, df # not the original df, filtered and has new col



def _pass2(subgraph_df: pd.DataFrame, max_days=MAX_PASS_2_DAYS) -> pd.DataFrame:
    subgraph_summaries = subgraph_df.groupby('subgraph_id').agg(
        manufacturer=('attr__norm__manufacturer', 'first'),
        model=('attr__norm__model_name', 'first'),
        os_name=('attr__norm__os_name', 'first'),

        client_name=('attr__norm__client_name', 'first'),
        os_version=('attr__norm__os_version', 'first'),

        min_ts=('timestamp', 'min'),
        max_ts=('timestamp', 'max'),

        client_v_start=('attr__norm__client_version', 'first'),
        client_v_end=('attr__norm__client_version', 'last'),

        first_node_id=('id', 'first'),
        last_node_id=('id', 'last'),
    ).reset_index()

    pairs = subgraph_summaries.merge(
        subgraph_summaries,
        on=['manufacturer', 'model', 'os_name', 'client_name'],
        suffixes=('_F', '_G')
    ) # df where every row is a pair of subgraphs (F and G) that match on hardware and software names

    if pairs.empty:
        return pd.DataFrame(columns=['id_a', 'id_b', 'type', 'provenance']), pairs

    # rule (a) - whole F must be temporally before whole G, but  they can't differ by more than max_days 
    valid_time_sequence = (pairs['max_ts_F'] < pairs['min_ts_G'])
    under_max_days = ((pairs['min_ts_G'] - pairs['max_ts_F']).dt.days <= max_days)
    pairs = pairs[valid_time_sequence & under_max_days] # prune

    # rule (b) is already satisfied by the subgraph conditions in pass 1
    # rule (c) - client upgrade from F to G
    valid_client_upgrade = pairs.apply(lambda x: compare_versions(x['client_v_start_G'], x['client_v_end_F']) != 'LT', axis=1)
    pairs = pairs[valid_client_upgrade]

    # rule (d) - OS upgrade from F to G
    valid_os_upgrade = pairs.apply(lambda x: compare_versions(x['os_version_G'], x['os_version_F']) == 'GT', axis=1)
    pairs = pairs[valid_os_upgrade] 

    if pairs.empty:
        return pd.DataFrame(columns=['id_a', 'id_b', 'type', 'provenance']), pairs

    edges = pairs[['last_node_id_F', 'first_node_id_G']].rename(
        columns={'last_node_id_F': 'id_a', 'first_node_id_G': 'id_b'}
    ).drop_duplicates()
    edges['type'] = 'OSUpgrade'
    edges['provenance'] = '{"upgrade_type": "OS version"}'
    return edges, pairs # don't really need to return pairs, for debug




def level2(df: pd.DataFrame) -> pd.DataFrame:
    events_df = df[df['table'] == 'events']
    if events_df.empty:
        return pd.DataFrame(columns=['id_a', 'id_b', 'type', 'provenance'])
    pass1_edges, subgraph_df = _pass1(events_df)
    pass2_edges, _ = _pass2(subgraph_df)
    combined = pd.concat([pass1_edges, pass2_edges], ignore_index=True)
    return combined.drop_duplicates()
