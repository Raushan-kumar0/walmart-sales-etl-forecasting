-- Target tables for the Walmart ETL pipeline. MySQL 8.0+
CREATE TABLE IF NOT EXISTS weekly_sales (
    store              INT           NOT NULL,
    dept               INT           NOT NULL,
    week_date          DATE          NOT NULL,      -- Friday that ends the sales week
    weekly_sales       DECIMAL(12,2) NOT NULL,      -- can be negative (returns > sales)
    is_negative_sales  BOOLEAN       NOT NULL,
    is_holiday_week    BOOLEAN       NOT NULL,      -- Super Bowl, Labor Day, Thanksgiving, Christmas
    store_type         CHAR(1)       NOT NULL,
    store_size         INT           NOT NULL,      -- square feet
    temperature        DECIMAL(6,2),
    fuel_price         DECIMAL(6,3),
    cpi                DECIMAL(10,4),
    unemployment       DECIMAL(6,3),
    total_markdown     DECIMAL(12,2) NOT NULL,      -- sum of MarkDown1-5 (0 = none recorded)
    has_markdown_data  BOOLEAN       NOT NULL,
    PRIMARY KEY (store, dept, week_date),           -- also stops duplicates getting in
    INDEX idx_ws_week (week_date)
);

CREATE TABLE IF NOT EXISTS etl_runs (
    run_id       INT AUTO_INCREMENT PRIMARY KEY,
    run_at       DATETIME NOT NULL,
    rows_in      INT NOT NULL,
    rows_loaded  INT NOT NULL,
    report_json  TEXT NOT NULL
);
