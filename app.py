from flask import Flask, render_template, url_for, request, session, redirect
from flask_pymongo import PyMongo
from flaskext.mysql import MySQL
import bcrypt
from datetime import *

app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'users'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/dbmsb'
mongo = PyMongo(app)

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'akshobhya'
app.config['MYSQL_DATABASE_DB'] = 'dbmsb'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
db = MySQL(app)


def insertIntoFaculty(username, name, designation, department, t_leaves=25, a_leaves=25, b_leaves=0, leaves_rqst=False):
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("INSERT INTO Faculty(username, name, designation, department, total_leaves, avail_leaves, borwd_leaves, leave_rqst) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)",
                   (username, name, designation, department, t_leaves, a_leaves, b_leaves, leaves_rqst))
    connect.commit()
    cursor.close()


def insertIntoLeaves(faculty_id, duration, start_date, status='pending', authority_comment='', faculty_comment='', approval_awaited='', sender_dept='', lvl=1, borwd_days=0):
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("INSERT INTO Leaves(faculty_id, duration, start_date, status, authority_comment, faculty_comment, approval_awaited, sender_dept, lvl, borwd_days) VALUES(%s, %s, %s, %s, %s, %s,  %s, %s, %s, %s)",
                   (faculty_id, duration, start_date, status, authority_comment, faculty_comment, approval_awaited, sender_dept, lvl, borwd_days))
    connect.commit()
    cursor.close()


def insertIntoLog(request_id, record, designation, name):
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("SELECT CURRENT_TIMESTAMP")
    timestamp = cursor.fetchall()[0][0]
    cursor.execute("INSERT INTO Log(timestamp, request_id, record, designation, name) VALUES(%s, %s, %s, %s, %s)",
                   (timestamp, request_id, record, designation, name))
    connect.commit()
    cursor.close()


@app.route('/')
def home():
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("select * from leaves")
    leave = cursor.fetchall()
    cursor.execute("select * from applydate")
    apply = cursor.fetchall()
    # print("--+++++++++++---")
    # print("--+++++++++++---")
    # print(leave)
    # print("--+++++++++++---")
    # print("--+++++++++++---")
    # print("--+++++++++++---")
    # print(apply)
    # print("--+++++++++++---")
    # print("--+++++++++++---")
    for acc in leave:
        reqid = acc[0]
        stdate = acc[3]
        status = acc[4]
        cursor.execute("select * from applydate where request_id = %s", reqid)
        val = cursor.fetchall()
        if len(val) == 0:
            continue
        # print("val = ", val)
        # print("reqid = ", reqid)
        # print("status = ", status)
        # print("stdate = ", stdate)

        appdate = val[0][2]
        # print("appdate = ", appdate)
        if (status == 'pending') and (appdate < stdate) and (stdate < date.today()):
            # print("+++++++++EXECUTING++++++++++++######$$$$$")
            cursor.execute("update leaves set status = %s, authority_comment = %s, approval_awaited = %s where  request_id = %s",
                           ('rejected', 'rejected(START DATE PASSED) - by SYSTEM;', '', reqid))

    connect.commit()
    cursor.close()
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


def userprofile():
    profile = mongo.db.profile
    profile_data = profile.find_one({'username': session['username']})
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM Faculty WHERE username = %s",
                   (session['username']))
    user_data = cursor.fetchall()
    cursor.execute("SELECT * FROM Leaves WHERE faculty_id = %s",
                   (user_data[0][0]))
    leave_data = cursor.fetchall()
    cursor.close()
    return render_template('user_profile.html', profile_data=profile_data, user_data=user_data, leave_data=leave_data)


@app.route('/login', methods=['POST'])
def login():
    users = mongo.db.users
    login_user = users.find_one({'name': request.form['username']})

    if login_user:
        if bcrypt.hashpw(request.form['password'].encode('utf8'), login_user['password']) == login_user['password']:
            session['username'] = request.form['username']
            session['logged_in'] = True
            profile = mongo.db.profile
            user_data = profile.find_one({'username': session['username']})
            if(user_data['designation'] == 'Faculty'):
                return userprofile()
            return adminprofile()

    return render_template("invalidup.html")


@app.route('/logout')
def logout():
    session['username'] = None
    session['logged_in'] = False
    return render_template('home.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'name': request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(
                request.form['password'].encode('utf8'), bcrypt.gensalt())
            users.insert(
                {'name': request.form['username'], 'password': hashpass})
            session['username'] = request.form['username']
            session['logged_in'] = True
            return render_template('save_info.html')
        return render_template('user_exists.html')
    return render_template('register.html')


@app.route('/editinfo')
def editinfo():
    profile = mongo.db.profile
    user_data = profile.find_one({'username': session['username']})
    return render_template('edit_info.html', user_data=user_data)


@app.route('/adminUpdate', methods=['POST', 'GET'])
def adminUpdate():
    if request.method == 'POST':
        profile = mongo.db.profile
        form_data = request.form
        profile.update({'username': form_data['name']}, {
                       "$set": {'designation': request.form['designation']}})
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("UPDATE Faculty SET designation = %s WHERE username = %s",
                   (request.form['designation'], request.form['name']))

    connect.commit()
    cursor.close()
    return render_template('updateProfiles.html')


@app.route('/updateinfo', methods=['POST', 'GET'])
def updateinfo():
    if request.method == 'POST':
        profile = mongo.db.profile
        form_data = request.form
        research_areas = []
        publication_title = []
        publication_desc = []
        for key, values in form_data.items():
            if key.find("research") != -1:
                research_areas.append(values)
            elif key.find("title") != -1:
                publication_title.append(values)
            elif key.find("description") != -1:
                publication_desc.append(values)
        profile.update({'username': session['username']}, {"$set": {'username': session['username'],
                                                                    'name': request.form['name'],
                                                                    'email': request.form['email'],
                                                                    'department': request.form['department'],
                                                                    'designation': request.form['designation'],
                                                                    'research': research_areas,
                                                                    'title': publication_title,
                                                                    'description': publication_desc}})
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("UPDATE Faculty SET name = %s, designation = %s, department = %s WHERE username = %s",
                   (request.form['name'], request.form['designation'], request.form['department'], session['username']))
    connect.commit()
    cursor.close()
    if(request.form['designation'] == 'Faculty'):
        return userprofile()
    return adminprofile()


@app.route('/saveinfo', methods=['POST', 'GET'])
def saveinfo():
    if request.method == 'POST':
        profile = mongo.db.profile
        data = request.form
        research_areas = []
        publication_title = []
        publication_desc = []
        for key, values in data.items():
            if key.find("research") != -1:
                research_areas.append(values)
            elif key.find("title") != -1:
                publication_title.append(values)
            elif key.find("description") != -1:
                publication_desc.append(values)
        canpass = True
        if request.form['designation'] != 'Faculty':
            connect = db.connect()
            cursor = connect.cursor()
            if request.form['designation'] == 'DFA':
                cursor.execute(
                    "select count(*) from faculty where designation = %s", ('DFA'))
                cnt = cursor.fetchall()

                if cnt[0][0]:
                    canpass = False
            elif request.form['designation'] == 'Director':
                cursor.execute(
                    "select count(*) from faculty where designation = %s", ('Director'))
                cnt = cursor.fetchall()

                if cnt[0][0]:
                    canpass = False
            else:
                dep = request.form['department']
                cursor.execute(
                    "select count(*) from faculty where department = %s and designation = %s", (dep, 'HoD'))
                cnt = cursor.fetchall()
                if cnt[0][0]:
                    canpass = False

        if not canpass:
            return render_template('nothappening.html')
        profile.insert({'username': session['username'],
                        'name': request.form['name'],
                        'email': request.form['email'],
                        'department': request.form['department'],
                        'designation': request.form['designation'],
                        'research': research_areas,
                        'title': publication_title,
                        'description': publication_desc})
        insertIntoFaculty(session['username'], request.form['name'], request.form['designation'],
                          request.form['department'], t_leaves=25, a_leaves=25, b_leaves=0, leaves_rqst=False)
        if request.form['designation'] == 'Faculty':
            return userprofile()
        else:
            return adminprofile()
    return 'something wrong occured'


@app.route('/profile<name>')
def profile(name):
    profile = mongo.db.profile
    user_data = profile.find_one({'username': name})
    return render_template('view_profile.html', user_data=user_data)


@app.route('/viewprofile')
def viewprofile():
    profile = mongo.db.profile
    user_data = profile.find_one({'username': session['username']})
    if user_data['designation'] == 'Faculty':
        return userprofile()
    return adminprofile()


@app.route('/proflist')
def proflist():
    profile = mongo.db.profile
    profiles = profile.find()
    return render_template('prof_list.html', profiles=profiles)


def adminprofile():
    profile = mongo.db.profile
    profile_data = profile.find_one({'username': session['username']})
    # print(profile_data)
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM Faculty WHERE username = %s",
                   (session['username']))
    user_data = cursor.fetchall()
    cursor.execute("SELECT * FROM Leaves WHERE faculty_id = %s",
                   (user_data[0][0]))
    leave_data = cursor.fetchall()
    if user_data[0][3] == "HoD":
        cursor.execute("SELECT * FROM Leaves WHERE approval_awaited = %s AND sender_dept = %s",
                       (user_data[0][3], user_data[0][4]))
    else:
        cursor.execute(
            "SELECT * FROM Leaves WHERE approval_awaited = %s AND status <> \'approved \'", (user_data[0][3]))
    pending_leaves = cursor.fetchall()
    cursor.close()
    return render_template('admin_profile.html', profile_data=profile_data, user_data=user_data, leave_data=leave_data, pending_leaves=pending_leaves)


@app.route('/modifyleave<request_id>')
def modifyleave(request_id):
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM Leaves WHERE request_id = %s", (request_id))
    leave_data = cursor.fetchall()
    cursor.close()
    return render_template("update_leave.html", leave_data=leave_data)


@app.route('/updateleave', methods=['POST', 'GET'])
def updateleave():
    if request.method == 'POST':
        form_data = request.form
        connect = db.connect()
        cursor = connect.cursor()
        cursor.execute(
            "SELECT designation, name FROM Faculty WHERE faculty_id = %s", (form_data['faculty_id']))
        res = cursor.fetchall()[0]
        cursor.execute(
            "SELECT * FROM LeaveRoute WHERE lvl = 1 AND send_from = %s", (res[0]))
        send_to = cursor.fetchall()[0][2]
        # cursor.execute("UPDATE Leaves SET duration=%s, start_date=%s,status=\'pending\' ,faculty_comment=%s, approval_awaited=%s ,lvl=1, borwd_days=%s WHERE request_id = %s",
        #                (form_data['duration'], form_data['start_date'], form_data['comment'], send_to, form_data['borwd_days'], form_data['request_id']))
        cursor.execute("UPDATE Leaves SET duration=%s, start_date=%s,status=\'pending\' ,faculty_comment=%s, approval_awaited=%s ,lvl=1, borwd_days=%s WHERE request_id = %s",
                       (form_data['duration'], form_data['start_date'], form_data['comment'], send_to, 0, form_data['request_id']))
        connect.commit()
        cursor.close()
        insertIntoLog(form_data['request_id'],
                      "leave request updated", res[0], res[1])
        if res[0] == 'Faculty':
            return userprofile()
        return adminprofile()


@app.route('/leaveapply<faculty_id>')
def leaveapply(faculty_id):
    return render_template("leave_application.html", faculty_id=faculty_id)


@app.route('/updateProfiles')
def updateProfiles():
    profile = mongo.db.profile
    profiles = profile.find()
    return render_template('updateProfiles.html', profiles=profiles)


@app.route('/viewleave<request_id>')
def viewleave(request_id):
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM Leaves WHERE request_id = %s", (request_id))
    leave_data = cursor.fetchall()
    cursor.close()
    return render_template("view_leave.html", leave_data=leave_data)


@app.route('/leaveaction', methods=['POST', 'GET'])
def leaveaction():
    if request.method == 'POST':
        form_data = request.form
        connect = db.connect()
        cursor = connect.cursor()

        cursor.execute("SELECT * FROM Leaves WHERE request_id = %s",
                       (form_data['request_id']))
        leave_data = cursor.fetchall()
        designation_ = leave_data[0][7]
        cursor.execute(
            "SELECT name FROM Faculty WHERE designation=%s", (designation_))
        name_ = cursor.fetchall()[0][0]
        if designation_ == 'HoD':
            cursor.execute(
                "SELECT name FROM Faculty WHERE designation = 'HoD' AND department=%s", (leave_data[0][8]))
            name_ = cursor.fetchall()[0][0]

        if form_data['action'] == 'approved':
            cursor.execute("SELECT * FROM LeaveRoute WHERE lvl = %s AND send_from = %s",
                           (leave_data[0][9]+1, leave_data[0][7]))

            # print("-------------------------")
            # print("-------------------------")
            # print("-------------------------")
            # print("-------------------------")
            # print("-------------------------")
            # print("leavel  = ", leave_data[0][9] + 1)
            # print("sending ot  = ", leave_data[0][7])
            xxx = cursor.fetchall()
            send_to = xxx[0][2]
            # print(send_to)
            # print("-------------------------")
            # print("-------------------------")
            # print("-------------------------")
            # print("-------------------------")
            # print("-------------------------")
            # print(cursor.fetchall())
            # print(send_to)
            start = leave_data[0][3]
            curr = date.today()
            if send_to == leave_data[0][7]:  # LEAVE APPROVED
                if (curr < start) or (send_to == 'Director'):
                    cursor.execute("UPDATE Leaves SET status = %s, authority_comment = %s, approval_awaited = %s WHERE request_id = %s", (
                        "approved", leave_data[0][6] + form_data['admin_comment']+" -by " + leave_data[0][7]+"; ", "", leave_data[0][0]))
                    cursor.execute(
                        "SELECT avail_leaves, borwd_leaves FROM Faculty WHERE faculty_id = %s", (leave_data[0][1]))
                    leaves = cursor.fetchall()[0]
                    cursor.execute("UPDATE Faculty SET avail_leaves=%s, borwd_leaves=%s, leave_rqst = %s WHERE faculty_id = %s", (
                        leaves[0] - leave_data[0][2], leaves[1] + leave_data[0][10], False, leave_data[0][1]))
                    connect.commit()
                    cursor.close()
                    insertIntoLog(
                        leave_data[0][0], "leave request approved", designation_, name_)
                elif (curr >= start) and (send_to == 'DFA'):
                    cursor.execute("UPDATE Leaves SET authority_comment = %s, approval_awaited = %s, lvl = %s WHERE request_id = %s", (
                        leave_data[0][6] + form_data['admin_comment']+" -by DFA" + "; ", 'Director', 3, leave_data[0][0]))
                    connect.commit()
                    cursor.close()
                    insertIntoLog(
                        leave_data[0][0], "leave request approved and forwarded", 'Director', 'dir')

            else:  # LEAVE FORWARED
                cursor.execute("UPDATE Leaves SET authority_comment = %s, approval_awaited = %s, lvl = %s WHERE request_id = %s", (
                    leave_data[0][6] + form_data['admin_comment']+" -by " + leave_data[0][7]+"; ", send_to, leave_data[0][9] + 1, leave_data[0][0]))
                connect.commit()
                cursor.close()
                insertIntoLog(
                    leave_data[0][0], "leave request approved and forwarded", designation_, name_)

        elif form_data['action'] == 'rejected':  # LEAVE REJECTED
            cursor.execute("UPDATE Leaves SET status = %s, authority_comment = %s, approval_awaited = %s WHERE request_id = %s", (
                "rejected", leave_data[0][6] + form_data['admin_comment']+" -by " + leave_data[0][7]+"; ", "", leave_data[0][0]))
            cursor.execute(
                "UPDATE Faculty SET leave_rqst = %s WHERE faculty_id = %s", (False, leave_data[0][1]))
            connect.commit()
            cursor.close()
            insertIntoLog(
                leave_data[0][0], "leave request rejected", designation_, name_)

        elif form_data['action'] == 'resubmit':
            cursor.execute("UPDATE Leaves SET status = %s, authority_comment = %s WHERE request_id = %s", (
                "resubmit", leave_data[0][6] + form_data['admin_comment']+" -by " + leave_data[0][7]+"; ", leave_data[0][0]))
            connect.commit()
            cursor.close()
            insertIntoLog(
                leave_data[0][0], "leave request to be resubmitted", designation_, name_)

    return adminprofile()


@app.route('/leave', methods=['POST', 'GET'])
def leave():
    if request.method == 'POST':
        data = request.form
        connect = db.connect()
        cursor = connect.cursor()
        cursor.execute(
            "SELECT * FROM Faculty WHERE faculty_id = %s", (data['faculty_id']))
        res = cursor.fetchall()
        cursor.execute(
            "select avail_leaves from faculty where faculty_id = %s", (data['faculty_id']))
        rem = cursor.fetchall()
        if(int(data['duration']) - 0 > res[0][6]):  # ///yha pr borwd_days tha
            return render_template("insuff.html", rem=rem)
        elif res[0][8] == 1:
            return render_template("again.html")
        else:
            cursor.execute(
                "SELECT * FROM LeaveRoute WHERE lvl = 1 AND send_from = %s", (res[0][3]))
            send_to = cursor.fetchall()[0][2]

            insertIntoLeaves(data['faculty_id'], data['duration'], data['start_date'], faculty_comment=data['comment'],
                             authority_comment='', approval_awaited=send_to, sender_dept=res[0][4], lvl=1, borwd_days=0)  # yha pr bhi
            cursor.execute("select * from leaves")
            x = cursor.fetchall()
            if len(x) != 0:
                reqid = x[len(x) - 1][0] + 1
            else:
                reqid = 1
            cursor.execute("insert into applydate values(%s, %s, %s, %s)",
                           (data['faculty_id'], reqid, date.today(), data['start_date']))
            cursor.execute(
                "UPDATE Faculty SET leave_rqst=True WHERE faculty_id = %s", (data['faculty_id']))
            connect.commit()
        cursor.close()
        if res[0][3] == 'Faculty':
            return userprofile()
        return adminprofile()


@app.route('/log')
def log():
    connect = db.connect()
    cursor = connect.cursor()
    cursor.execute("SELECT * FROM Log")
    log_entries = cursor.fetchall()
    cursor.close()
    return render_template("log.html", log_entries=log_entries)


if __name__ == '__main__':
    app.secret_key = 'secret123'
    try:
        app.run(debug=True)
    except IndexError as error:
        redirect("user_exists.html")
