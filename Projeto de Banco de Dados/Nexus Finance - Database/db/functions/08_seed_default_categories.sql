-- Semeia as categorias padrão de um novo usuário (chamada no cadastro)
CREATE OR REPLACE FUNCTION seed_default_categories(p_user_id BIGINT) RETURNS VOID AS $$
BEGIN
  INSERT INTO categories(user_id, name, type) VALUES
    (p_user_id, 'Moradia',      'expense'),
    (p_user_id, 'Alimentação',  'expense'),
    (p_user_id, 'Transporte',   'expense'),
    (p_user_id, 'Saúde',        'expense'),
    (p_user_id, 'Educação',     'expense'),
    (p_user_id, 'Lazer',        'expense'),
    (p_user_id, 'Vestuário',    'expense'),
    (p_user_id, 'Contas Fixas', 'expense'),
    (p_user_id, 'Assinaturas',  'expense'),
    (p_user_id, 'Outros',       'expense'),
    (p_user_id, 'Salário',      'income'),
    (p_user_id, 'Freelance',    'income'),
    (p_user_id, 'Aluguel',      'income'),
    (p_user_id, 'Dividendos',   'income'),
    (p_user_id, 'Pensão',       'income'),
    (p_user_id, 'Outros',       'income');
END;
$$ LANGUAGE plpgsql;
