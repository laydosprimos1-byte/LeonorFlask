PROJETO LEONOR ARMando - FLASK + SQLITE

1. No Termux:
pkg update
pkg install python -y

2. Entre na pasta do projeto:
cd LeonorFlask

3. Instale:
pip install -r requirements.txt

4. Execute:
python app.py

5. Abra no navegador do Android:
http://127.0.0.1:5000

BANCO DE DADOS:
O arquivo database.db é criado automaticamente. Os utilizadores e dados do perfil ficam no SQLite.

RECUPERAÇÃO:
No modo local, ao pedir recuperação, o link aparece no terminal. Para recuperação por email de verdade, configure SMTP antes de colocar o sistema na internet.

SEGURANÇA:
Antes de publicar, troque SECRET_KEY, use HTTPS, configure email real e não use credenciais de email dentro do código.
