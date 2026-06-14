-- Valor atual da posição: quantidade × último preço unitário. NULL se sem cotação.
CREATE OR REPLACE FUNCTION position_value(p_investment_id BIGINT) RETURNS NUMERIC AS $$
DECLARE qty NUMERIC; price NUMERIC;
BEGIN
  SELECT quantity INTO qty FROM investments WHERE id = p_investment_id;
  IF NOT FOUND THEN RETURN NULL; END IF;

  SELECT market_value INTO price FROM value_history
    WHERE investment_id = p_investment_id ORDER BY date DESC LIMIT 1;
  IF price IS NULL THEN RETURN NULL; END IF;

  RETURN qty * price;
END;
$$ LANGUAGE plpgsql STABLE;
