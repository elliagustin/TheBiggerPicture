# -*- coding: utf-8 -*-
"""
Created on Sun Nov  2 17:07:56 2025

@author: BernardoElli
"""

class Validator:
    def __init__(self, api_client=None, timeframe="5m"):
        self.api = api_client
        self.timeframe = timeframe

    def quick_validate(self, df_prices_1h, entry, tp, sl,
                       start_time, lookahead_hrs, quick_only=True):
        # 1h coarse check
        status = self._coarse_check(df_prices_1h, entry, tp, sl, start_time, lookahead_hrs)

        # if ambiguous and allowed, resolve via api
        if status == "ambiguous" and not quick_only and self.api:
            detailed = self._detailed_validate_api(start_time, entry, tp, sl)
            return detailed  # e.g., {"status": "tp_hit"} / {"status": "sl_hit"}

        return {"status": status}
