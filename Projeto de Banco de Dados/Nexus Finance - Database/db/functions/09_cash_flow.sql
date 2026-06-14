-- Fluxo de caixa por período: realizado (transações settled) + projetado
-- (bills a_vencer + recorrências NÃO materializadas, virtuais). Saldo abre na
-- soma de todas as carteiras. Não conta em dobro (materializadas já são bills).
CREATE OR REPLACE FUNCTION cash_flow(
  p_user_id BIGINT, p_start DATE, p_end DATE, p_granularity TEXT DEFAULT 'monthly'
) RETURNS TABLE(
  bucket DATE, kind TEXT, inflow NUMERIC, outflow NUMERIC, net NUMERIC, running_balance NUMERIC
) AS $$
DECLARE v_unit TEXT; opening NUMERIC; run NUMERIC; rec RECORD; proj_from DATE;
BEGIN
  v_unit := CASE p_granularity WHEN 'daily' THEN 'day' WHEN 'weekly' THEN 'week' ELSE 'month' END;
  proj_from := GREATEST(p_start, CURRENT_DATE + 1);   -- projeção começa amanhã

  -- saldo de abertura: todas as carteiras + transações settled antes de p_start
  SELECT COALESCE(SUM(w.initial_balance), 0) INTO opening FROM wallets w WHERE w.user_id = p_user_id;
  opening := opening + COALESCE((
    SELECT SUM(CASE WHEN type = 'inflow' THEN amount ELSE -amount END)
    FROM transactions WHERE user_id = p_user_id AND status = 'settled' AND date < p_start), 0);
  run := opening;

  FOR rec IN
    WITH realized AS (
      SELECT date_trunc(v_unit, t.date)::date AS b,
             SUM(CASE WHEN t.type = 'inflow'  THEN t.amount ELSE 0 END) AS infl,
             SUM(CASE WHEN t.type = 'outflow' THEN t.amount ELSE 0 END) AS outf,
             'realized' AS src
      FROM transactions t
      WHERE t.user_id = p_user_id AND t.status = 'settled' AND t.date BETWEEN p_start AND p_end
      GROUP BY 1
    ),
    proj_bills AS (
      SELECT date_trunc(v_unit, bl.due_date)::date AS b,
             SUM(CASE WHEN bl.type = 'receivable' THEN bl.amount ELSE 0 END) AS infl,
             SUM(CASE WHEN bl.type = 'payable'    THEN bl.amount ELSE 0 END) AS outf,
             'projected' AS src
      FROM bills bl
      WHERE bl.user_id = p_user_id AND bl.cancelled_at IS NULL
        AND bl.due_date BETWEEN proj_from AND p_end
        AND bill_status(bl.id) = 'a_vencer'
      GROUP BY 1
    ),
    proj_rec AS (
      SELECT date_trunc(v_unit, d.dt)::date AS b,
             SUM(CASE WHEN r.type = 'receivable' THEN r.amount ELSE 0 END) AS infl,
             SUM(CASE WHEN r.type = 'payable'    THEN r.amount ELSE 0 END) AS outf,
             'projected' AS src
      FROM recurrences r
      CROSS JOIN LATERAL recurrence_dates(r.id, proj_from, p_end) AS d(dt)
      WHERE r.user_id = p_user_id AND r.active AND r.materialize = false
      GROUP BY 1
    ),
    merged AS (
      SELECT * FROM realized
      UNION ALL SELECT * FROM proj_bills
      UNION ALL SELECT * FROM proj_rec
    )
    SELECT b,
           CASE WHEN bool_or(src = 'realized') THEN 'realized' ELSE 'projected' END AS kind,
           SUM(infl) AS inflow, SUM(outf) AS outflow
    FROM merged GROUP BY b ORDER BY b
  LOOP
    run := run + (rec.inflow - rec.outflow);
    bucket := rec.b; kind := rec.kind;
    inflow := rec.inflow; outflow := rec.outflow;
    net := rec.inflow - rec.outflow; running_balance := run;
    RETURN NEXT;
  END LOOP;
END;
$$ LANGUAGE plpgsql STABLE;
