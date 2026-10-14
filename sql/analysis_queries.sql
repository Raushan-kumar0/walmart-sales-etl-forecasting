-- Questions asked of the clean weekly_sales table. analysis.py runs each block
-- (marked by "-- name:") and saves the result to outputs/<name>.csv

-- name: like_for_like_years
-- Total sales per year over the same calendar window (5 Feb - 26 Oct) so the years compare fairly
SELECT YEAR(week_date)                      AS year,
       COUNT(DISTINCT week_date)            AS weeks,
       ROUND(SUM(weekly_sales) / 1e6, 1)    AS sales_millions,
       ROUND(SUM(weekly_sales) / COUNT(DISTINCT week_date) / 1e6, 2) AS avg_week_millions   -- fair even if week counts differ
FROM weekly_sales
WHERE DATE_FORMAT(week_date, '%m-%d') BETWEEN '02-05' AND '10-26'
GROUP BY YEAR(week_date)
ORDER BY year;

-- name: holiday_vs_normal_weeks
WITH weeks AS (
    SELECT week_date, MAX(is_holiday_week) AS holiday, SUM(weekly_sales) AS total
    FROM weekly_sales
    GROUP BY week_date
)
SELECT CASE WHEN holiday = 1 THEN 'Holiday week' ELSE 'Normal week' END AS week_type,
       COUNT(*)                         AS weeks,
       ROUND(AVG(total) / 1e6, 2)       AS avg_sales_millions
FROM weeks
GROUP BY week_type;

-- name: top_weeks
-- The 6 biggest weeks of the whole period
SELECT week_date,
       MAX(is_holiday_week)             AS flagged_holiday,
       ROUND(SUM(weekly_sales) / 1e6, 1) AS sales_millions
FROM weekly_sales
GROUP BY week_date
ORDER BY SUM(weekly_sales) DESC
LIMIT 6;

-- name: store_types
WITH per_store AS (
    SELECT store, store_type, MAX(store_size) AS size, AVG(weekly_total) AS avg_week
    FROM (SELECT store, store_type, store_size, week_date, SUM(weekly_sales) AS weekly_total
          FROM weekly_sales GROUP BY store, store_type, store_size, week_date) w
    GROUP BY store, store_type
)
SELECT store_type,
       COUNT(*)                                 AS stores,
       ROUND(AVG(size))                         AS avg_size_sqft,
       ROUND(AVG(avg_week))                     AS avg_weekly_sales_per_store,
       ROUND(SUM(avg_week) / SUM(size), 2)      AS weekly_sales_per_sqft
FROM per_store
GROUP BY store_type
ORDER BY store_type;

-- name: top_departments
SELECT dept,
       ROUND(SUM(weekly_sales) / 1e6, 1)                                         AS sales_millions,
       ROUND(100 * SUM(weekly_sales) / (SELECT SUM(weekly_sales) FROM weekly_sales), 1) AS share_pct
FROM weekly_sales
GROUP BY dept
ORDER BY SUM(weekly_sales) DESC
LIMIT 10;

-- name: most_seasonal_departments
-- Peak week vs an average week, for departments selling at least $500k a week on average
WITH dept_weeks AS (
    SELECT dept, week_date, SUM(weekly_sales) AS total
    FROM weekly_sales
    GROUP BY dept, week_date
)
SELECT dept,
       ROUND(AVG(total))                      AS avg_week,
       ROUND(MAX(total))                      AS peak_week,
       ROUND(MAX(total) / AVG(total), 1)      AS peak_to_average
FROM dept_weeks
GROUP BY dept
HAVING AVG(total) >= 500000
ORDER BY peak_to_average DESC
LIMIT 6;
