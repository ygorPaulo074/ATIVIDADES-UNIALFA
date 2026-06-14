-- Total investido (em R$): Σ aportes − Σ retiradas
CREATE OR REPLACE FUNCTION invested_total(p_investment_id BIGINT) RETURNS NUMERIC AS $$
DECLARE total NUMERIC;
BEGIN
  SELECT COALESCE(SUM(CASE WHEN type = 'deposit' THEN amount ELSE -amount END), 0)
    INTO total FROM contributions WHERE investment_id = p_investment_id;
  RETURN total;
END;
$$ LANGUAGE plpgsql STABLE;
