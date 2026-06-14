-- Trigger: coerência tipo da conta x tipo da categoria
CREATE OR REPLACE FUNCTION trg_bill_type_coherence() RETURNS TRIGGER AS $$
DECLARE cat_type category_type;
BEGIN
  IF NEW.category_id IS NULL THEN RETURN NEW; END IF;
  SELECT type INTO cat_type FROM categories WHERE id = NEW.category_id;
  IF (NEW.type = 'receivable' AND cat_type <> 'income')
  OR (NEW.type = 'payable'    AND cat_type <> 'expense') THEN
    RAISE EXCEPTION 'Categoria (%) incompatível com conta %', cat_type, NEW.type;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bill_type_coherence BEFORE INSERT OR UPDATE ON bills
  FOR EACH ROW EXECUTE FUNCTION trg_bill_type_coherence();
