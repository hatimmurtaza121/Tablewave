from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DATABASE = 'new_database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'").fetchall()
    conn.close()
    return render_template('index.html', tables=[t[0] for t in tables])

@app.route('/table/<table_name>')
def table(table_name):
    conn = get_db_connection()
    if table_name == 'salaries':
        query_one_address = '''
        SELECT s.id, s.name, s.salary
        FROM salaries s
        '''
        salaries_with_one_address = conn.execute(query_one_address).fetchall()

        query_all_addresses = '''
        SELECT a.emid, a.address, a.postal
        FROM addresses a
        WHERE a.emid IN (SELECT id FROM salaries)
        '''
        all_addresses = conn.execute(query_all_addresses).fetchall()
        
        from collections import defaultdict
        addresses_by_emid = defaultdict(list)
        for emid, address, postal in all_addresses:
            addresses_by_emid[emid].append((address, postal))
        
        combined_results = []
        for row in salaries_with_one_address:
            emid = row['id']
            combined_results.append({
                'id': emid,
                'name': row['name'],
                'salary': row['salary'],
                'all_addresses': addresses_by_emid[emid]
            })

        rows = combined_results
        columns = [
            ('id', 'INTEGER'),
            ('name', 'VARCHAR'),
            ('salary', 'INTEGER'),
            ('all_addresses', 'TEXT')
        ]
    else:
        rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
        columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'").fetchall()
    conn.close()
    
    return render_template('index.html', table_name=table_name, rows=rows, columns=columns, tables=[t[0] for t in tables])


@app.route('/create_table', methods=('GET', 'POST'))
def create_table():
    if request.method == 'POST':
        table_name = request.form['table_name']
        num_columns = int(request.form['num_columns'])
        columns = [(request.form[f'col_name_{i}'], request.form[f'col_type_{i}']) for i in range(1, num_columns + 1)]
        
        col_definitions = ", ".join([f"{name} {dtype}" for name, dtype in columns])
        create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {col_definitions})"
        
        conn = get_db_connection()
        conn.execute(create_stmt)
        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))

    return render_template('index.html')


@app.route('/create_row/<table_name>', methods=('POST',))
def create_row(table_name):
    row_data = {key: value for key, value in request.form.items() if key not in ['submit', 'address[]', 'postal[]']}
    col_names = ", ".join(row_data.keys())
    placeholders = ", ".join(["?" for _ in row_data.values()])
    values = tuple(row_data.values())

    conn = get_db_connection()

    if table_name == 'salaries':
        conn.execute(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})", values)
        conn.commit()

        salary_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        addresses = request.form.getlist('address[]')
        postals = request.form.getlist('postal[]')

        for address, postal in zip(addresses, postals):
            conn.execute("INSERT INTO addresses (emid, address, postal) VALUES (?, ?, ?)", (salary_id, address, postal))

    else:
        conn.execute(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})", values)

    conn.commit()
    conn.close()
    return redirect(url_for('table', table_name=table_name))



@app.route('/update_row/<table_name>/<int:row_id>', methods=('POST',))
def update_row(table_name, row_id):
    row_data = {key: value for key, value in request.form.items() if key != 'submit'}
    set_clause = ", ".join([f"{col_name} = ?" for col_name in row_data.keys()])
    values = list(row_data.values())

    conn = get_db_connection()

    if table_name == 'salaries':
        conn.execute(f"UPDATE {table_name} SET name = ?, salary = ? WHERE id = ?", (row_data['name'], row_data['salary'], row_id))
        addresses = request.form.getlist('address[]')
        postals = request.form.getlist('postal[]')

        conn.execute("DELETE FROM addresses WHERE emid = ?", (row_id,))
        for address, postal in zip(addresses, postals):
            conn.execute("INSERT INTO addresses (emid, address, postal) VALUES (?, ?, ?)", (row_id, address, postal))

    else:
        values.append(row_id)
        conn.execute(f"UPDATE {table_name} SET {set_clause} WHERE id = ?", values)
    
    conn.commit()
    conn.close()
    return redirect(url_for('table', table_name=table_name))


@app.route('/delete_row/<table_name>/<int:row_id>', methods=('POST',))
def delete_row(table_name, row_id):
    conn = get_db_connection()
    conn.execute(f"DELETE FROM {table_name} WHERE id = ?", (row_id,))
    if table_name == 'salaries':
        conn.execute(f"DELETE FROM {'addresses'} WHERE emid = ?", (row_id,))

    conn.commit()
    conn.close()
    return redirect(url_for('table', table_name=table_name))

if __name__ == '__main__':
    app.run(debug=True)
