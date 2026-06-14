-- Ajusta o dia ao mês (dia inexistente -> último dia do mês)
CREATE OR REPLACE FUNCTION clamp_day(p_month_start DATE, p_day INT) RETURNS DATE AS $$
DECLARE last_day INT;
BEGIN
  last_day := EXTRACT(DAY FROM (p_month_start + INTERVAL '1 month - 1 day'))::INT;
  RETURN p_month_start + (LEAST(p_day, last_day) - 1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;
