import pandas as pd
import io
import uuid
import csv
import json
from base import BaseParser
from parseresult import ParseResult
from errors import FileLevelError, RecordLevelError
from time_utils import parse_date, unix_ms
from typing import Callable, Any, List, Tuple

pd.options.mode.copy_on_write = True

class CSVParser(BaseParser):


    @classmethod
    def parse(cls, s: str, filename: str, cfg: List[dict], default="", **kwargs):
        """
        example cfg: [
            { "temporal": "", "category": "",  "parser": { ... }, "fields": [ ... ] }, 
            ...
        ]
        """
        result = ParseResult()

        try:
            df, bad_lines = cls.str_to_df(s)
            for msg in bad_lines:
                result.add_error(RecordLevelError(msg, context={'filename': filename}))
        except Exception as e:
            result.add_error(FileLevelError(f"Fatal CSV error: {str(e)}", 
                                          context={'filename': filename}))
            return result

        if df.empty:
            result.add_error(RecordLevelError("DataFrame is empty after parsing", 
                                            context={'filename': filename}))
            return result
        
        result.stats['total_records_attempted'] = len(df)
        
        for single_cfg in cfg:
            e, s, cfg_errors = cls.df_to_elements(filename, df, single_cfg, default, **kwargs)
            result.events.extend(e)
            result.states.extend(s)
            result.stats['records_successful'] += len(e) + len(s)
            for err_msg in cfg_errors:
                result.add_error(RecordLevelError(err_msg, context={'filename': filename}))
        
        return result
        
        

    @classmethod
    def df_to_elements(cls, filename: str, df: pd.DataFrame, 
                        single_cfg: dict, # { "temporal": "", "category": "",  "parser": { ... }, "fields": [ ... ] }
                        default: Any = "", **kwargs):
        """
        Returns: (events, states, errors)
        - errors: list of RecordLevelError objects
        """
        parser_cfg = single_cfg.get("parser", {})
        fields = single_cfg.get("fields", [])
        temporal = single_cfg.get("temporal", "event")
        category = single_cfg.get("category", "default")
        cfg_errors = []

        try:
            if "filter" in parser_cfg:
                df = cls.filter_df(df, parser_cfg["filter"])
            if "drop_duplicates" in parser_cfg:
                df = cls.drop_duplicates(df, parser_cfg["drop_duplicates"])
        except Exception as e:
            cfg_errors.append(RecordLevelError(f"filter/dedup error: {str(e)}", 
                                               context={'filename': filename}))
            # Continue with un-filtered data
 
        try:
            original_record_col = df.apply(lambda r: json.dumps(r.to_dict()), axis=1)
            mapped_field_df = cls.map_fields(df, fields, default)
        except Exception as e:
            cfg_errors.append(RecordLevelError(f"Field mapping error: {str(e)}", 
                                               context={'filename': filename}))
            # Return empty if mapping completely failed
            return [], [], cfg_errors

        mapped_field_df['id'] = [uuid.uuid4().hex for _ in range(len(mapped_field_df))]
        mapped_field_df['sketch_id'] = kwargs.get('sketch_id', default)
        mapped_field_df['timeline_id'] = kwargs.get('timeline_id', default)
        mapped_field_df['source_file'] = filename
        mapped_field_df['source_line'] = (df.index + 1).astype(str)
        mapped_field_df['category'] = category
        mapped_field_df['original_record'] = original_record_col
        mapped_field_df['created_at'] = kwargs.get('created_at', default)

        events, states = [], []
        if temporal == "event":
            events = mapped_field_df.to_dict(orient='records')
        elif temporal == "state":
            states = mapped_field_df.to_dict(orient='records')
        return events, states, cfg_errors




    @classmethod
    def str_to_df(cls, s: str):
        # static, inherited
        bad_lines = []
        def handle_bad_line(line):
            bad_lines.append(f"Malformed or ragged line skipped: {','.join(line[:5])}...")
            return None
        
        try:
            # engine='python' is more robust for bad lines and allows the callable
            df = pd.read_csv(
                io.StringIO(s),
                dtype=str,
                keep_default_na=False,
                on_bad_lines=handle_bad_line,
                engine='python',
                quoting=csv.QUOTE_MINIMAL
            )
        except Exception as e:
            raise RuntimeError(f"fatal CSV parsing error: {str(e)}")
        
        return df, bad_lines


    @classmethod
    def filter_df(cls, df, filter_cfg):
        """
        filter_cfg = 
        EITHER 
            {source: "event", op: "==", value: "Email Added"} 
        OR
            {
                logic: "all" or"any", 
                conditions: [ {source: "event", op: "==", value: "Email Added"} , ...]
            }
        only one level of all/any nesting supported for now
        """
        if not filter_cfg or df.empty:
            return df
        
        logic = filter_cfg.get("logic")
        if logic is not None:  # if filter_cfg is {logic: ..., conditions: [...]}
            child_masks = [cls.make_bool_mask(df, cond) for cond in filter_cfg.get("conditions", [])]
            if child_masks == []:
                return df
            if logic.lower() == "any":
                combined_mask = child_masks[0]
                for m in child_masks[1:]:
                    combined_mask = combined_mask | m
            elif logic.lower() == "all":
                combined_mask = child_masks[0]
                for m in child_masks[1:]:
                    combined_mask = combined_mask & m
        
        else: # if filter_cfg is a single condition
            combined_mask = cls.make_bool_mask(df, filter_cfg)

        filtered_df = df[combined_mask]
        return filtered_df
    
    @classmethod
    def make_bool_mask(cls, df, cfg: dict, regex=False) -> pd.Series:

        if not isinstance(cfg, dict): return cls.default_mask(df, False)
        field = cfg.get("field")
        op = cfg.get("op")
        value = cfg.get("value")
        if field is None or op is None or value is None: 
            return cls.default_mask(df, False)
        
        if field not in df.columns:
            return cls.default_mask(df, True)  # missing field means no filtering
        
        value = str(value)
        col = df[field].astype(str)
        if op in cls.op_mapping["eq"]: return col == value
        if op in cls.op_mapping["ne"]: return col != value
        if op in cls.op_mapping["contains"]: return col.str.contains(value, regex=regex, na=False)
        if op in cls.op_mapping["startswith"]: return col.str.startswith(value, na=False)
        if op in cls.op_mapping["endswith"]: return col.str.endswith(value, na=False)
        return cls.default_mask(df, False)

    @classmethod
    def default_mask(cls, df: pd.DataFrame, boolean: bool) -> pd.Series:
        if boolean not in [True, False]:
            boolean = False
        return pd.Series([boolean] * len(df), index=df.index)

    

    @classmethod
    def drop_duplicates(cls, df, dupe_cfg: dict):
        # dupe_cfg = { subset: ["Recovery ID"], keep: "row_completeness"}
        try:
            subset = dupe_cfg.get("subset", [])
            keep = dupe_cfg.get("keep", "first")
            if keep not in ["first", "last", "row_completeness"]:
                # TODO log warning eventually
                keep = "first"
            
            if keep == "row_completeness":
                # Add temp columns for null count and original order
                null_counts = df.replace('', pd.NA).notnull().sum(axis=1)
                df = df.assign(temp_null_count=null_counts, temp_orig_index=range(len(df)))
                df = df.sort_values(['temp_null_count', 'temp_orig_index'], ascending=[False, True])
                df = df.drop_duplicates(subset=subset, keep='first')
                df = df.sort_values('temp_orig_index').drop(columns=['temp_null_count', 'temp_orig_index'])
            else:
                df = df.drop_duplicates(subset=subset, keep=keep)
            return df
        
        except Exception as e:
            raise RuntimeError(f"drop_duplicates error: {str(e)}")



    @classmethod
    def map_fields(cls, df: pd.DataFrame, fields: List[dict], default: Any = "") -> pd.DataFrame:
        field_names = []
        newdf = pd.DataFrame(index=df.index)
        for f in fields:
            name, source, ftype = f.get("name"), f.get("source"), f.get("type", "string")
            field_names.append(name)

            if isinstance(source, list):
                source = [s for s in source if s in df.columns]
                if not source:
                    col = pd.Series(default, index=df.index)
                elif f.get("transform", "").lower() == "coalesce":
                    coalesced_col = df[source[0]].replace('', pd.NA)
                    for s in source[1:]:
                        coalesced_col = coalesced_col.combine_first(df[s].replace('', pd.NA))
                    col = coalesced_col
                else:
                    col = df[source[0]]
            else:
                col = df[source] if source in df.columns else pd.Series(default, index=df.index)

            if ftype in ["datetime", "timestamp", "date"]:
                col = col.apply(lambda x: unix_ms(parse_date(x)))

            newdf[name] = col.replace('', pd.NA).fillna(default)

        return newdf