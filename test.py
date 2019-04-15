import xmlrpclib

server = xmlrpclib.ServerProxy("http://localhost:8081/")
print(server.check_path('/tmp'))
