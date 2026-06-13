-- Analizar si la info de las tablas esta duplicada

select Datetime, Open_EURUSD, High_EURUSD, Low_EURUSD, Close_EURUSD, Volume_EURUSD, count(*) 
from landing.ForexBidH1
group by Datetime, Open_EURUSD, High_EURUSD, Low_EURUSD, Close_EURUSD, Volume_EURUSD
having count(*)>1 
order by 1 

WITH Dupes AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY Datetime, Open_EURUSD, High_EURUSD, Low_EURUSD, Close_EURUSD, Volume_EURUSD
               ORDER BY Datetime, Open_EURUSD, High_EURUSD, Low_EURUSD, Close_EURUSD, Volume_EURUSD
           ) AS rn
    FROM landing.ForexBidH1	
)
DELETE FROM Dupes
WHERE rn > 1;

select Datetime, Open_EURUSD, High_EURUSD, Low_EURUSD, Close_EURUSD, Volume_EURUSD
from landing.ForexBidH1 where datetime = '2022-05-12 17:00:00.000'

--delete from landing.ForexBidH1 
--where  datetime in ( '2022-05-12 17:00:00.000' , '2021-10-03 22:00:00.000')
--and Open_EURUSD is null


-- Analizar si la info de las tablas esta duplicada
select Datetime, count(*) as total from landing.ForexAskH1 group by Datetime having count(*)>1  order by 1 

select Datetime, count(*) as total from landing.ForexBidH1 group by Datetime having count(*)>1  order by 1 

select Datetime, count(*) as total from landing.ForexBidM5 group by Datetime having count(*)>1  order by 1 

select Datetime, count(*) as total from landing.vw_ForexAskH1_WithQuality group by Datetime having count(*)>1 order by 1 

--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- 
---  ask
--delete FROM landing.ForexAskH1
--WHERE DATEPART(MINUTE, Datetime) != 0

SELECT Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD
FROM landing.ForexAskH1
ORDER BY Datetime; -- to csv

--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- 
-- bid
SELECT Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD
FROM landing.ForexBidH1
ORDER BY Datetime; -- to csv

INSERT INTO landing.ForexBidH1 (Datetime, Open_EURUSD, High_EURUSD, Low_EURUSD, Close_EURUSD, Volume_EURUSD)
VALUES ('2022-05-12 06:00:00', 1.04969, 1.05015, 1.04883, 1.04897, 4517),
       ('2022-05-12 07:00:00', 1.04767, 1.04830, 1.04639, 1.04647, 7686);

SELECT Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD
FROM landing.ForexBidH1
WHERE Datetime >= '2022-05-12 05:00:00'
AND Datetime <= '2022-05-12 08:00:00'
ORDER BY Datetime; 

--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

select Datetime, count(*) as total from landing.ForexBidM5 group by Datetime having count(*)>1  order by 1 

SELECT Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD
FROM landing.ForexBidM5
ORDER BY Datetime ; -- to csv


--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

SELECT max(Datetime), Min(Datetime) FROM landing.ForexBidM5;

SELECT max(Datetime), Min(Datetime) FROM landing.ForexAskM5;

SELECT Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD
FROM landing.ForexAskM5
ORDER BY Datetime ; -- to csv

-- duplicates
select Datetime, count(*) as total from landing.ForexAskM5 group by Datetime having count(*)>1  order by 1  -- empty

--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

SELECT  top 1 Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD FROM landing.ForexAskH1;

--Open = 1.03726
--Close = 1.03701
SELECT max(High_EURUSD),    min(Low_EURUSD), sum(Volume_EURUSD) FROM landing.ForexAskM5 
where Datetime >= '2025-01-02 04:00:00'
and Datetime < '2025-01-02 05:00:00';

--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

SELECT  top 1 Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD 
FROM landing.ForexAskH1 where datetime = '2021-07-29 01:00:00'
--Datetime	Open_EURUSD	High_EURUSD	Low_EURUSD	Close_EURUSD	Volume_EURUSD
--2021-07-29 01:00:00.000	1.18511	1.18511	1.18441	1.18483	3376

--{'instrument': 'EUR_USD',
-- 'granularity': 'H1',
-- 'candles': [{'complete': True,
--   'volume': 2461,
--   'time': '2021-07-29T01:00:00.000000000Z',
--   'ask': {'o': '1.18444', 'h': '1.18509', 'l': '1.18426', 'c': '1.18502'}}]}

SELECT min(Datetime) as Datetime, max(High_EURUSD) as High,    min(Low_EURUSD) as Low, sum(Volume_EURUSD) as Vol, count(*) as Total_rows
FROM landing.ForexAskM5 
where Datetime >= '2024-05-20 17:00:00' 
and Datetime < '2024-05-20 18:00:00' ;

---
SELECT  top 1 Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD 
FROM landing.ForexAskH1 where datetime = '2021-07-29 01:00:00'
--Datetime	Open_EURUSD	High_EURUSD	Low_EURUSD	Close_EURUSD	Volume_EURUSD
--2021-07-29 01:00:00.000	1.18511	1.18511	1.18441	1.18483	3376
--Datetime	Open_EURUSD	High_EURUSD	Low_EURUSD	Close_EURUSD	Volume_EURUSD
--2021-07-29 01:00:00.000	1.18444	1.18509	1.18426	1.18502	2461

--

SELECT Datetime,    Open_EURUSD,    High_EURUSD,    Low_EURUSD,    Close_EURUSD,    Volume_EURUSD
FROM landing.ForexAskM5 
where Datetime >= '2024-05-20 17:00:00' 
and Datetime < '2024-05-20 18:00:00' ;