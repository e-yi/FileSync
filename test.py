import xmlrpclib

server_power = xmlrpclib.ServerProxy("http://localhost:8081/")
print(server_power.check_path('/tmp'))
