-- Gera as parcelas (bills) de um parcelamento; última absorve o arredondamento
CREATE OR REPLACE FUNCTION generate_installments(p_plan_id BIGINT) RETURNS INT AS $$
DECLARE
  p installment_plans%ROWTYPE;
  base_amount NUMERIC; last_amount NUMERIC;
  i INT; month_start DATE; due DATE;
BEGIN
  SELECT * INTO p FROM installment_plans WHERE id = p_plan_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'installment_plan % não encontrado', p_plan_id; END IF;

  base_amount := trunc(p.total_amount / p.total_installments, 2);
  last_amount := p.total_amount - base_amount * (p.total_installments - 1);

  FOR i IN 1..p.total_installments LOOP
    month_start := (date_trunc('month', p.purchase_date) + ((i - 1) || ' month')::interval)::date;
    due := clamp_day(month_start, EXTRACT(DAY FROM p.purchase_date)::int);

    INSERT INTO bills(
      user_id, type, description, amount, due_date,
      category_id, payment_method_id, installment_plan_id, installment_number
    ) VALUES (
      p.user_id, 'payable',
      p.description || ' (' || i || '/' || p.total_installments || ')',
      CASE WHEN i < p.total_installments THEN base_amount ELSE last_amount END,
      due, p.category_id, p.payment_method_id, p_plan_id, i
    );
  END LOOP;

  RETURN p.total_installments;
END;
$$ LANGUAGE plpgsql;
