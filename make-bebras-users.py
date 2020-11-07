#!/usr/bin/python
import csv
import sys
import mysql.connector
import json
import md5

config = None
mydb = None

def makeId():
	return random.randint(1000000000000000,100000000000000000000)

def makePassword():
	letters = string.ascii_letters
	return ''.join(random.choice(letters) for i in range(10))
   
def makeSalt():
	return md5(makePassword())
	
def makeGroupCode():
	letters = string.ascii_lowercase + string.digits
	return ''.join(random.choice(letters) for i in range(10))
	
	 
def createOrFindTeacher(name, email):
	cursor = mydb.cursor()
	email = email.lower().strip()

	cursor.execute("SELECT ID FROM users WHERE officialEmail = %s", (email))
	res = cursor.fetchAll()
	if len(res) != 0:
		return (res[0], '[Sendt i tidligere epost]')
	
	print ("Creating user %s for %s"%(name, email))
	id = makeId()
	salt = makeSalt()
	password = makePassword()
	encryptedPassword = md5(password+salt)
	
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

	cursor.execute("INSERT INTO users (id, firstName, lastName, officialEmail, officialValidated, " +
		"alternativeEmail, alternativeEmailValidated, salt, passwordMd5, recoverCode, validated, " +
		"allowMultipleSchools, isAdmin, registrationDate, lastLoginDate, comment, iVersion) VALUES " +
		"(%d, %s, %s, %s, %d,   %s, %d, %s, %s, %s, %d,  %d, %d, %s, %s, %s, %d)",
		(id, name, '', email, True,
		None, False, salt, encryptedPassword, '', True,
		True, False, timestamp, timestamp, '', 0))
	cursor.commit()
	return (id, password)

def createOrFindSchool(name, userId):
	name = name.strip()
	cursor = mydb.cursor()	
	cursor.execute("SELECT ID FROM school WHERE name = %s AND userId = %d", (name, userId))
	res = cursor.fetchAll()
	if len(res) != 0:
		return res[0]
		
	print ("Creating school %s"%name)
	schoolId = makeId()
	cursor.execute("INSERT INTO school (id, userId, name, region, address, zipcode, city, country, " +
		"nbStudents, validated, saniMsg, iVersion) VALUES " +
		"(%d, %d, %s, %s, %s, %s, %s, %s,   %d %d %s %d)",
		(id, userId, name, 'ukjent', '', '', '', 'Norge',
		1000, 1, '', 0))
		
	cursor.execute("INSERT INTO school_user (id, schoolId, userId, confirmed, iVersion) VALUES " +
		"(%d, %d, %d, %d, %d)",
		(makeId(), schoolId, userId, 1, 0))
				
	cursor.commit()
	
	return schoolId


def createContestGroupsIfNeccessary(userId, schoolId, schoolName, contestId, expectedStart):
	cursor = mydb.cursor()	
	cursor.execute("SELECT ID FROM `group` WHERE userId = %d AND schoolId = %d AND contestId = %d", 
		(userId, schoolId, contestId))
	res = cursor.fetchAll()
	if len(res) != 0:
		print("School already have %d contest groups"%len(res))
		return None
	
	codes = []
	for i in range(3):
		groupCode = makeGroupCode()
		secureCode = makeGroupCode()
		cursor.execute("INSERT INTO `group` (id, schoolId, grade, gradeDetails, userId, name, " +
			"nbStudents, contestID, minCategory, maxCategory, language, " +
			"code, password, expectedStartTime, participationType, iVersion) VALUES " +
			"(%d, %d, %d, %s, %d, %s,   %d, %d, %s, %s, %s,  %s, %s, %s, %s, %d)",
			(makeId(), schoolId, 11, '', userId, "%s - %d"%(schoolName, i),
			100, contestId, '', '', '',
			groupCode, secureCode, expectedStart, 'Official', 0))
		codes.append(groupCode)
	cursor.commit()

def createTeacherIfNeccessary(row, line, csv_writer):
	if row[3] == '':
		return False
	if row[3].find('@') == -1:
		print("Missing email in line %d"%line)
		return False
	print(", ".join(row))
	
	userId,password = createOrFindTeacher(row[2],row[3])	
	schoolId = createOrFindSchool(row[1])
	contestGroups = createContestGroupsIfNeccessary(userId, schoolId, row[1].strip(), config.get("contestId"), config.get("expectedStart"))
	if contestGroups:
		csv_writer.writeRow([row[2], row[3], row[1], contestGroups[0], contestGroups[1], contestGroups[2]])
	return True
	
def main(argv):
	if len(argv) != 2:
		print("Usage: make-bebras-users [inputfile] [outputfile]")
		sys.exit(1)
	with open('make-bebras-users.conf') as config_file:
		config = json.load(config_file)
		if not (config.get("hostname") and config.get("username") and config.get("database") and config.get("password") 
				and config.get("contestId") and config.get("expectedStart")):
			print("Missing or invalid configuration file.")
			sys.exit(1)
		if config.hostname != "TEST":
			mydb = mysql.connector.connect(
				host=config.get("hostname"),
				user=config.get("username"),
				password=config.get("password"),
				database=config.get("database")
			)
			
	with open(argv[0], mode='r') as input_file:
		csv_reader = csv.reader(input_file, delimiter=';')
		with open(argv[1], mode='wa') as output_file:
			csv_writer = csv.writer(output_file, delimiter=';')
			
			line_count = 0
			imported = 0
			for row in csv_reader:
				if line_count == 0 and row[3] == 'Epost':
					print "Skipping first line, as it appears to be a column header"
				else:
					if createTeacherIfNeccessary(row, line_count + 1, csv_writer):
						imported += 1
				line_count += 1
			print('Processed %d lines, creating %d new teachers.'%(line_count,imported))
	
if __name__ == "__main__":
   main(sys.argv[1:])
