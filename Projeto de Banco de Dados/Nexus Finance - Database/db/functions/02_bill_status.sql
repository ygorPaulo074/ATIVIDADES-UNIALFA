-- Status derivado de uma conta (ver docs/03-status.md)
CREATE OR REPLACE FUNCTION bill_status(p_bill_id BIGINT) RETURNS TEXT AS $$
DECLARE b bills%ROWTYPE; paid NUMERIC;
BEGIN
  SELECT * INTO b FROM bills WHERE id = p_bill_id;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF b.cancelled_at IS NOT NULL THEN RETURN 'cancelada'; END IF;

  SELECT COALESCE(SUM(amount), 0) INTO paid
    FROM transactions WHERE bill_id = p_bill_id AND status = 'settled';

  IF    paid >= b.amount          THEN RETURN 'quitada';
  ELSIF paid > 0                  THEN RETURN 'parcial';
  ELSIF b.due_date < CURRENT_DATE THEN RETURN 'atrasada';
  ELSE  RETURN 'a_vencer';
  END IF;
END;
$$ LANGUAGE plpgsql STABLE;
