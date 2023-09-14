import sqlite3

class DbStorage:
    def __init__(self, connection_string=":memory:"):
        self.connection_string = connection_string
    
    def connect(self):
        self.db = sqlite3.connect(self.connection_string)
        self.cursor = self.db.cursor()

    def insert_or_select_cmd(self, name:str) -> int:
        results = self.cursor.execute("SELECT id, name FROM commands WHERE name = ?", (name, )).fetchall()

        if len(results) == 0:
            self.cursor.execute("INSERT INTO commands (name) VALUES (?)", ("query_cmd", ))
            return self.cursor.lastrowid
        elif len(results) == 1:
            return results[0][0]
        else:
            print("this should not be happening: " + str(results))
            return -1
    
    def setup_db(self):
        # create tables
        self.cursor.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, model text, context_size INTEGER)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS commands (id INTEGER PRIMARY KEY, name string unique)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS queries (run_id INTEGER, round INTEGER, cmd_id INTEGER, query TEXT, response TEXT, duration REAL, tokens_query INTEGER, tokens_response INTEGER)")

        # insert commands
        self.query_cmd_id = self.insert_or_select_cmd('query_cmd')
        self.analyze_response_id = self.insert_or_select_cmd('analyze_response')
        self.state_update_id = self.insert_or_select_cmd('update_state')

    def create_new_run(self, model, context_size):
        self.cursor.execute("INSERT INTO runs (model, context_size) VALUES (?, ?)", (model, context_size))
        return self.cursor.lastrowid

    def add_log_query(self, run_id, round, cmd, result, answer):
        self.cursor.execute("INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (run_id, round, self.query_cmd_id, cmd, result, answer.duration, answer.tokens_query, answer.tokens_response))

    def add_log_analyze_response(self, run_id, round, cmd, result, answer):
        self.cursor.execute("INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (run_id, round, self.analyze_response_id, cmd, result, answer.duration, answer.tokens_query, answer.tokens_response))

    def add_log_update_state(self, run_id, round, cmd, result, answer):

        if answer != None:
            self.cursor.execute("INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (run_id, round, self.state_update_id, cmd, result, answer.duration, answer.tokens_query, answer.tokens_response))
        else:
            self.cursor.execute("INSERT INTO queries (run_id, round, cmd_id, query, response, duration, tokens_query, tokens_response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (run_id, round, self.state_update_id, cmd, result, 0, 0, 0))

    def get_round_data(self, run_id, round):
        rows = self.cursor.execute("select cmd_id, query, response, duration, tokens_query, tokens_response from queries where run_id = ? and round = ?", (run_id, round)).fetchall()

        for row in rows:
            if row[0] == self.query_cmd_id:
                cmd = row[1]
                size_resp = str(len(row[2]))
                duration = f"{row[3]:.4f}"
                tokens = f"{row[4]}/{row[5]}"
            if row[0] == self.analyze_response_id:
                reason = row[2]
                analyze_time = f"{row[3]:.4f}"
                analyze_token = f"{row[4]}/{row[5]}"

        result = [duration, tokens, cmd, size_resp, analyze_time, analyze_token, reason]
        return result

    def get_cmd_history(self, run_id):
        rows = self.cursor.execute("select query, response from queries where run_id = ? and cmd_id = ? order by round asc", (run_id, self.query_cmd_id)).fetchall()

        result = []

        for row in rows:
            result.append([row[0], row[1]])

        return result
    

    def commit(self):
        self.db.commit()