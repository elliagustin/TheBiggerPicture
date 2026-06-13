# -*- coding: utf-8 -*-
"""
Created on Wed Jan 28 04:27:43 2026

@author: BernardoElli_P
"""


STRATEGY_RULES = [
    {
        "name": "1EJ-v2",    
        "environments": ["demo"],  
        "pairs": ["EUR_JPY"],
        "directions": ["Long","Short"],        
        "days": [0,1,2,3,4],                                              
        "hours": [13,14,18,20,23],                   
        "max_spread": 50,                                                       
        "volume": {
            "demo": 5000,
            "live": 1000
        },
                
        "params": {
            "long_model_key": 1,
            "short_model_key": 2,
            "offset_points": 200,
            "tp_points": 150,
            "sl_points": 150,
            "threshold": 0.8,
            "contrarian_direction_flag": False
        }
    }
    ,{
        "name": "N2",
        "environments": ["live", "demo"],
        "pairs": ["USD_CHF","CAD_JPY"], 
        "directions": ["Long","Short"],        
        "days": [0,2,3,4],                                                   
        "hours": [7,8,10,11,12,13,14,15],                                     
        "max_spread": 50,               
        "volume": {
            "demo": 5000,
            "live": 1000
        },                                                   

        "params": {
            "long_model_key": 1,
            "short_model_key": 2,
            "offset_points": 150,
            "tp_points": 150,
            "sl_points": 200,
            "threshold": 0.77,
            "contrarian_direction_flag": False
        }
    }
    ,{
        "name": "2b2",
        "environments": ["demo","live"],
        "pairs": ["EUR_GBP","NZD_USD"], 
        "directions": ["Long","Short"],        
        "days": [0,1,2,3,4],                                                   
        "hours": [1,2,3,      6,7,8,9,10,11,12,13,14,15,    20],                                     
        "max_spread": 50,                 
        "volume": {
            "demo": 5000,
            "live": 1000
        },                                                

        "params": {
            "long_model_key": 1,
            "short_model_key": 2,
            "offset_points": 150,
            "tp_points": 150,
            "sl_points": 200,
            "threshold": 0.77,
            "contrarian_direction_flag": False
        }
    }
    ,{
        "name": "AUD_USD",
        "environments": ["demo", "live"],
        "pairs": ["AUD_USD"], 
        "directions": ["Long","Short"],        
        "days": [0,1,2,3,4],                                                   
        "hours": [1,   3,4,5,6,7,8,   10,11,   13,14,15,16,17,18,19,20],                                     
        "max_spread": 50,                                                                   
        "volume": {
            "demo": 5000,
            "live": 1000
        },
        
        "params": {
            "long_model_key": 1,
            "short_model_key": 2,
            "offset_points": 100,
            "tp_points": 200,
            "sl_points": 200,
            "threshold": 0.77,
            "contrarian_direction_flag": False
        }
    }
    ,{
        "name": "Demo",    
        "environments": ["demo"],        
        "pairs": [
            'AUD_CAD','AUD_CHF','AUD_JPY','AUD_NZD','AUD_USD',
            'CAD_CHF','CAD_JPY',
            'CHF_JPY',
            'EUR_AUD','EUR_CAD','EUR_CHF','EUR_GBP','EUR_JPY','EUR_NZD','EUR_USD'],
        "directions": ["Long","Short"],        
        "days": [0,1,2,3,4],                                                    
        "hours": [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23],                   
        "max_spread": 50,                                                       
        "volume": {
            "demo": 1000,
            "live": 1000
        },
        
        # strategy params (used directly to trade)
        "params": {
            "long_model_key": 1,
            "short_model_key": 2,
            "offset_points": 50,
            "tp_points": 150,
            "sl_points": 150,
            "threshold": 0.77,
            "contrarian_direction_flag": False
        }
    }

]








