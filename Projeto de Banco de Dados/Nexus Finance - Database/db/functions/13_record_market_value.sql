-- Upsert do preço unitário do dia (chamado pelo job de sincronização brapi)
CREATE OR REPLACE FUNCTION record_market_value(
  p_investment_id BIGINT, p_date DATE, p_price NUMERIC
) RETURNS VOID AS $$
BEGIN
  INSERT INTO value_history(investment_id, date, market_value)
  VALUES (p_investment_id, p_date, p_price)
  ON CONFLICT (investment_id, date) DO UPDATE SET market_value = EXCLUDED.market_value;
END;
$$ LANGUAGE plpgsql;
