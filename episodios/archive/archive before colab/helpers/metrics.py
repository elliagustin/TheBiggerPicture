# -*- coding: utf-8 -*-
"""
Created on Sat Oct 25 11:45:14 2025

@author: BernardoElli
"""

import pandas as pd
import sklearn.metrics as sk


class Metrics:
    def __init__(self, results: pd.DataFrame):
        self.results = results

    def compute(self):
        r = self.results.copy()

        # --- Classification metrics ---
        y_true = r['actual'].astype(int)
        y_pred = r['predicted'].astype(int)

        entries = int((y_pred == 1).sum())  # cantidad de señales activas

        precision = sk.precision_score(y_true, y_pred, zero_division=0)
        recall = sk.recall_score(y_true, y_pred, zero_division=0)
        
        # tn, fp, fn, tp = sk.confusion_matrix(y_true, y_pred).ravel()        
        cm = sk.confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()


        # --- Build dictionary ---
        metrics = {
            "Entries": entries,
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "TP": int(tp),
            "FP": int(fp),
            "TN": int(tn),
            "FN": int(fn)
        }

        return metrics

