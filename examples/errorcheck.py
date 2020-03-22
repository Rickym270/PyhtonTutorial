#!/opt/netmgt/bin/python3

'''
  Author:   Ricky Martinez
  Purpose:  Error Checking for scripts. This assumes that all scripts have valid logging when there is a 
            crontab job that is executed
            This program is seperated into phases. First check for any syntax errors, then for any runtime errors.
            Syntax Error Check:
              This is done by:
              - Obtaining the language that the program is in.
                - ``` grep -rl '^#!/.*python$' <DIRECTORY> ```
                - ``` grep -rl '^#!/.*python3$' <DIRECTORY>```
                NOTE: In python it's either python 2.# or 3.# so check for both
              - Compiling the programs but not executing them.
                - ``` python -m compileall <DIRECTORY> ```


            Log Error Checker:
              Parse through all logs and see if there is any files that include the word, traceback.
                - A range of lines in a text is better obtained by using the Streamline Editor(sed) command.
                  - ``` sed --file=<FILENAME> -n -e '/<STARTWORD>/,/<ENDWORD>/ p' ```

            TODO: Investigate what PERL errors look like
            NOTE: Currently only supports PYTHON 2/3 and PERL
'''
from pprint import pprint
import os
import subprocess as sub

import sys
sys.path.append(<SOMEPATH>)

### NOTE: Edit this to find files in other directories ###
DIRECTORIES_TO_CHECK = [<PATH1>,
                        <PATH2>,
                        <PATH3>,
                        <PATH4>,]

### NOTE: Add files to ignore from the checks ###
IGNORE_FILES = [<PATH1>,
                <PATH2>,
                <PATH3>,
                <PATH4>]

FILE_CONFIGS = {
                  'python'  : {
                                'shebang'     : '#!/opt/netmgt/bin/python',
                                'syntax_cmd'  : '/opt/netmgt/bin/python -m py_compile ',
                                'extensions'  : ['.py'],
                                'ignore'      : ['.pyc']
                              },
                  'python3' : {
                                'shebang'     : '#!/opt/netmgt/bin/python3',
                                'syntax_cmd'  : '/opt/netmgt/bin/python3 -m py_compile ',
                                'extensions'  : ['.py'],
                                'ignore'      : ['.pyc']
                              },
                  'perl'    : {
                                'shebang'     : '#!/opt/netmgt/bin/perl',
                                'syntax_cmd'  : '/opt/netmgt/bin/perl -c ',
                                'extensions'  : ['.pl'],
                                'flagwords'   : ['']
                              },
                  'php'    : {
                                'shebang'     : '',
                                'syntax_cmd'  : '',
                                'extensions'  : ['.php'],
                              }
                }
TABLE_HEADERS = ['Script Name', 'Syntax Error', 'Runtime Error']

class ErrorChecker(object):
    def __init__(self):
        self.files = []
        # If more filetypes, add to this dictionary as well as FILE_CONFIGS
        self.allfiles = {'python':[],'python3':[],'perl':[]}
        self.run_err = "None"

    def _connect_db(self):
        '''
            Connect to the database and save the cursor and db handle to ``` self ```
        '''
        import MySQLdb

        #GET DB info
        with open(DBINFO_PATH,'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if i == 0:
                    host = line[:-1]
                elif i == 1:
                    username = line[:-1]
                elif i == 2:
                    password = line[:-1]

        #CONNECT to DB
        self.db = MySQLdb.connect(host='127.0.0.1',user=username,passwd=password, db="NMG", unix_socket = <SOCKETPATH>)
        self.cur = self.db.cursor()

    def _get_files(self):
        '''
            Get all files within the DIRECTORIES_TO_CHECK directories. Append the directory to get the full complete path (absolute path)
        '''
        for directory in DIRECTORIES_TO_CHECK:
            filenames = [directory + f for f in os.listdir(directory) if '.'        in f and
                                                                         'pyc'  not in f and
                                                                         'swp'  not in f and
                                                                         'old'  not in f and
                                                                         'test' not in f]


            for filename in filenames:
                if filename in IGNORE_FILES:
                    continue;
                else:
                    self.files.append(filename)

    def _get_crontab(self, user='netmgt_user'):
        '''
            Get the crontab for specified user
        '''
        crontab_cmd = "crontab -l -u {}".format(user)
        try:
            crontab_counter = sub.Popen(crontab_cmd, stdout= sub.PIPE, stderr=sub.PIPE, shell=True)
        except Exception as e:
            raise

        crontab_out, crontab_err = crontab_counter.communicate()
        crontab_out = crontab_out.decode()
        crontab_err = crontab_err.decode()

        if crontab_err: print("ERROR Obtaining crontab: {}".format(crontab_err))

        self.crontab =  crontab_out

    def _python_resolver(self, filename):
        '''
            Since all python files have the extension ```.py```, we have to figure out which python to run (2 or 3).
            This is done by running the grep command. First python2 is tried, then python3

            returns: <string> py2/py3
        '''
        py2_grep_cmd = 'grep -rl "^#!/.*python$" {}'.format(filename)
        filetype_counter = sub.Popen(py2_grep_cmd, stdout= sub.PIPE, stderr=sub.PIPE, shell=True)
        filetype_output, filetype_err = filetype_counter.communicate()
        filetype_output = filetype_output.decode().strip()

        if filetype_output:
            return 'py2'

        if not filetype_output:
            py3_grep_cmd = 'grep -rl "^#!/.*python3$" {}'.format(filename)
            filetype_counter = sub.Popen(py3_grep_cmd, stdout= sub.PIPE, stderr=sub.PIPE, shell=True)
            filetype_output, filetype_err = filetype_counter.communicate()
            filetype_output = filetype_output.decode()

            if filetype_output:
                return 'py3'

    def _get_log_file(self, script, crontab):
        '''
            Get the corresponding logfile, if there is a cronjob and the logfile is not ``` dev/null ```
        '''
        self.log_file = []
        crontab = crontab.split('\n')

        for index, line in enumerate(crontab):
            if script in line:
                cron_line = crontab[index]
                if 'dev/null' not in cron_line and cron_line[0] != "#":
                    try:
                        self.log_file.append(cron_line.split('>>')[1].strip().split(' ')[0])
                    except Exception as e:
                        self.log_file.append(cron_line.split('>')[1].strip().split(' ')[0])

                else: continue

    def _get_filetype(self, filename):
        '''
            Appends the files into their respective dictionary key:
                python, python3 or perl
        '''
        for language in FILE_CONFIGS:
            extensions = FILE_CONFIGS[language]['extensions']
            for extension in extensions:
                if extension in filename:
                    if 'py' in extension and filename not in self.allfiles['python'] and\
                                             filename not in self.allfiles['python3']:
                        real_extension = self._python_resolver(filename)

                        if real_extension == 'py2':
                            self.allfiles['python'].append(filename)

                        if real_extension == 'py3':
                            self.allfiles['python3'].append(filename)

                    if 'pl' in extension and filename not in self.allfiles['perl']:
                        self.allfiles['perl'].append(filename)

    def _get_syntax_errors(self, filetype, script):
        '''
            Runs py_compile or perl -c on all scripts. The correct form of python is determined by the filetype found at _get_filetype.
        '''
        self.syn_err = "None"
        self.script = script

        syntax_cmd = "{} {}".format(FILE_CONFIGS[filetype]['syntax_cmd'], script)
        syntax_counter = sub.Popen(syntax_cmd, stdout= sub.PIPE, stderr=sub.PIPE, shell=True)
        syntax_output, syntax_err = syntax_counter.communicate()
        syntax_output = syntax_output.decode().strip()
        syntax_err = syntax_err.decode().strip()

        if syntax_err and "OK" not in syntax_err:
            self.syn_err = syntax_err

  def _get_runtime_errors(self, filetype, log):
      '''
        Check for errors specified in the logs. The following files are ignored because their logs are really long...
            - blockedIPChecker.log, blockedIpChecker_init.log, portal_tools.log, Device.log
        The Directory where the logs are stored and being checked is ``` /var/log/twns/ ```
      '''

      sed_cmd = "sed -n -e '/Traceback/,/Error/ p' {}".format(log)
      sed_counter = sub.Popen(sed_cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
      sed_out, sed_err = sed_counter.communicate()
      sed_out = sed_out.decode().strip()
      self.run_err = 'None'
      if sed_out:
          self.run_err = sed_out
      if not sed_out:
          #logger.info("NO runtime errors found for {}".format(script))
          self.lines = []
          self.run_err = ''

          try:
              with open(log[0]) as f:
                  self.lines = f.readlines()
          except Exception as e:
              self.run_err = "Unable to open {}. {}".format(log, e)

          ### NOTE: Add any conidition for runtime errors here
          for line in self.lines:
              line = line.strip()
              if 'Permission denied' in line:
                  self.run_err = 'Permission Denied'
              if "py" in filetype:
                  start = False
                  error = ''

                  if 'Traceback' in line or "error" in line.lower() or "errors" in line.lower():
                      start = True
                  if start:
                      if "{}</br>".format(line) not in error and "ERROR" not in line:
                          error = "{}</br>".format(line)

                  if not line or '' == line or line.startswith('-'):
                      start = False

                  if error:
                      if error not in self.run_err:
                          self.run_err += error

    def get_db_info(self):
        '''
            Returns cursor and database handlers. This is a public method that allows access to self.db and self.cursor
        '''
        self._connect_db()
        return self.db, self.cur

    def get_files(self):
        '''
            Returns list of all files in directories
        '''
        self._get_files()
        return self.files

    def get_crontab(self):
        '''
            Returns crontab
        '''
        self._get_crontab()
        return self.crontab

    def get_AllFileData(self):
        '''
            Get complete data for a file
        '''
        files = self.get_files()

        for filename in files:
            self._get_filetype(filename)

        return self.allfiles

    def get_log_file(self, script):
        '''
            Get log file for script
            Returns: <string> log_file if there is one
                     False if none is found.
        '''
        self._get_log_file(script, self.crontab)
        return self.log_file

    def get_syntax_errors(self, filetype, script):
        self._get_syntax_errors(filetype, script)
        return self.syn_err

    def get_runtime_errors(self, filetype, log):
        self._get_runtime_errors(filetype, log)
        return self.run_err

    def insert_err(self, script, synerr, runerr):
        '''
            Try to INSERT SyntaxErrors into the Database ```NightCheckErrors```
            If it fails, submit a WARNING
            If it doesnt fail, commit
        '''
        dec_runerr = []
        synerr = self.db.escape_string(synerr).decode()

        if type(runerr) == list:
            for error in runerr:
                error = self.db.escape_string(error).decode()
                dec_runerr.append(error)

        if not synerr:
            synerror = "None"
        if not dec_runerr or (len(dec_runerr) == 1 and dec_runerr[0] == "None"):
            dec_runerr = "None"
        else:
            continue

        insert_query = 'INSERT INTO NightCheckErrors(`caller`,`syntax_err`,`runtime_err`) VALUES(%s, %s, %s);'

        try:
            if type(dec_runerr) == list and len(dec_runerr) == 1:
                self.cur.execute(insert_query, (script, synerr, dec_runerr[0]))
            else:
                self.cur.execute(insert_query, (script, synerr, dec_runerr))
        except Exception as e:
            pass
        finally:
            self.db.commit()

    def get_okay(self):
        query = "SELECT * FROM NightCheckErrors WHERE (`syntax_err` = 'None' OR runtime_err ='None') AND Date(`timestamp`) = CURDATE();"
        self.cur.execute(query)
        return self.cur.fetchall();

    def get_errors(self):
        query = "SELECT `caller`, `syntax_err`, `runtime_err` FROM NightCheckErrors WHERE (`syntax_err` !='None' OR runtime_err !='None') AND Date(`timestamp`) = CURDATE();"
        self.cur.execute(query)
        return self.cur.fetchall();

    def get_all(self):
        query = 'SELECT * FROM NightCheckErrors WHERE Date(`timestamp`) = CURDATE();'
        self.cur.execute(query)
        return self.cur.fetchall()[0];

    def get_time(self):
        query = "SELECT `timestamp` FROM NightCheckErrors WHERE (`syntax_err` !='None' OR runtime_err !='None') AND Date(`timestamp`) = CURDATE();"
        self.cur.execute(query)

        try:
            return self.cur.fetchone();
        except Exception:
            query = "SELECT `timestamp` FROM NightCheckErrors WHERE Date(`timestamp`) = CURDATE();"
            self.cur.execute(query)

         return self.cur.fetchall();

    def print_info(self, script, syntax, runtime):
        from texttable import Texttable

        table = Texttable();
        table.reset()
        table.set_cols_align(["l","l","l"])
        table.add_rows([
                          ['Script Name', 'Syntax Error', 'Runtime Error'],
                          [script, syntax, list(error for error in runtime)],
                  ])
        print(table.draw())

    def clearTable(self):
        #TODO: Get oldest record
        DATEDIFF_QUERY = 'SELECT DATEDIFF((SELECT `timestamp` FROM NightCheckErrors ORDER BY `timestamp` LIMIT 1), CURDATE());'
        self.cur.execute(DATEDIFF_QUERY)
        date_diff = self.cur.fetchone()[0]

        if date_diff and date_diff < -7:
            self.cur.execute("TRUNCATE NightCheckErrors");

if __name__ == "__main__":
    from pprint import pprint
    ### Determine filetype first ###
    nc = ErrorChecker()
    nc._connect_db()
    nc.clearTable()
    run_error, syn_error = "None", "None"

    files = nc.get_AllFileData()
    crontab = nc.get_crontab()
    results = {}

    ## Check for syntax errors
    for filetype, scripts in files.items():
        scripts = list(sorted(set(scripts)))
        for ind, script in enumerate(scripts):
            results.update({script  :{'log'       :   'None',
                                      'syntax'    :   'None',
                                      'runtime'   :   'None'}
                          })
            run_errors = []

            print("Checking syntax errors for {}... ".format(script), end = "")
            syn_error = nc.get_syntax_errors(filetype, script)
            print("Done.")
            if syn_error:
                print("Syntax Error:\n\t{}".format(syn_error))
                results[script]['syntax'] = syn_error
                print("\n\n")

            # Get runtime errors now. First get the corresponding log file
            print("Obtaining log file for {}... ".format(script), end = "")
            log_file = nc.get_log_file(script)
            results[script]['log'] = log_file
            if not log_file:
                print("No log found. Unable to check from runtime errors.")
                run_errors.append('None')
                continue
            else:
                print("Done.")
                print("Obtained: {}".format(list(log for log in log_file)))
                print("\n\n")
                if len(log_file) > 1:
                    for log in log_file:
                        if log:
                            print("Checking runtime errors at {} for {}... ".format(log, script), end="")
                            run_error = nc.get_runtime_errors(filetype, log)
                            run_errors.append(run_error.strip().replace("\\",""))
                if len(log_file) == 1:
                    if log_file:
                        run_error = nc.get_runtime_errors(filetype, log_file)
                        if run_error:
                            run_errors.append(run_error.strip().replace("\\",""))
                        else:
                            run_errors.append("None")
                results[script]['runtime'] = run_errors

    for script in results:
        nc.insert_err(script, results[script]['syntax'], results[script]['runtime'])
    pprint(results)
