-- Rentabilidade (em R$): valor da posição − total investido. NULL se sem cotação.
CREATE OR REPLACE FUNCTION investment_return(p_investment_id BIGINT) RETURNS NUMERIC AS $$
DECLARE pv NUMERIC;
BEGIN
  pv := position_value(p_investment_id);
  IF pv IS NULL THEN RETURN NULL; END IF;
  RETURN pv - invested_total(p_investment_id);
END;
$$ LANGUAGE plpgsql STABLE;
