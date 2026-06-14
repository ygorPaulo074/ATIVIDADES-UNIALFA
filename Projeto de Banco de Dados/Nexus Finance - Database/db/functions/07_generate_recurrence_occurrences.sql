-- Materializa como bills as ocorrências da recorrência até p_until (sem duplicar)
CREATE OR REPLACE FUNCTION generate_recurrence_occurrences(
  p_recurrence_id BIGINT, p_until DATE
) RETURNS INT AS $$
DECLARE r recurrences%ROWTYPE; d DATE; created INT := 0;
BEGIN
  SELECT * INTO r FROM recurrences WHERE id = p_recurrence_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'recurrence % não encontrada', p_recurrence_id; END IF;

  FOR d IN SELECT recurrence_dates(p_recurrence_id, r.start_date, p_until) LOOP
    IF NOT EXISTS (SELECT 1 FROM bills WHERE recurrence_id = r.id AND due_date = d) THEN
      INSERT INTO bills(
        user_id, type, description, amount, due_date,
        category_id, payment_method_id, recurrence_id
      ) VALUES (
        r.user_id, r.type, r.description, r.amount, d,
        r.category_id, r.payment_method_id, r.id
      );
      created := created + 1;
    END IF;
  END LOOP;

  RETURN created;
END;
$$ LANGUAGE plpgsql;
