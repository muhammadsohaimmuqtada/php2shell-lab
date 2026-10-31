.PHONY: doctor list start stop board serve hints reset

doctor:
	./labctl doctor
list:
	./labctl list
start:
	./labctl start $(V)
stop:
	./labctl stop $(V)
board:
	./labctl board
serve:
	./labctl serve
reset:
	./labctl reset
