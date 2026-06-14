-- Datas das ocorrências de uma recorrência (virtual, não grava) no intervalo [from, until].
-- Respeita end_date / occurrences_count. Reutilizada por generate_... e por cash_flow.
CREATE OR REPLACE FUNCTION recurrence_dates(
  p_recurrence_id BIGINT, p_from DATE, p_until DATE
) RETURNS SETOF DATE AS $$
DECLARE r recurrences%ROWTYPE; occ_date DATE; k INT := 0; limit_date DATE;
BEGIN
  SELECT * INTO r FROM recurrences WHERE id = p_recurrence_id;
  IF NOT FOUND OR NOT r.active THEN RETURN; END IF;
  limit_date := LEAST(p_until, COALESCE(r.end_date, p_until));

  LOOP
    IF r.frequency = 'weekly' THEN
      occ_date := r.start_date + (k * r.interval_count) * 7;   -- mantém o dia da semana
    ELSIF r.frequency = 'monthly' THEN
      occ_date := clamp_day(
        (date_trunc('month', r.start_date) + ((k * r.interval_count) || ' month')::interval)::date,
        r.reference_day);
    ELSE
      occ_date := clamp_day(
        (date_trunc('month', r.start_date) + ((k * r.interval_count) || ' year')::interval)::date,
        r.reference_day);
    END IF;

    EXIT WHEN occ_date > limit_date;
    EXIT WHEN r.occurrences_count IS NOT NULL AND k >= r.occurrences_count;
    IF occ_date >= p_from THEN RETURN NEXT occ_date; END IF;
    k := k + 1;
  END LOOP;
END;
$$ LANGUAGE plpgsql STABLE;
