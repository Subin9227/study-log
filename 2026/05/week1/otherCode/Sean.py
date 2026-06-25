"""
todo.py — 아주 간단한 할일 관리 CLI

사용법:
  python3 todo.py add "할일 내용"
  python3 todo.py list
  python3 todo.py done 1
  python3 todo.py remove 1

json으로 데이터 저장
argparse 사용할 것
"""

import argparse
import json
import os

DATE_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")

def load_tasks() :
	if not os.path.exists(DATE_FILE):
		return[]
	with open(DATE_FILE, 'r', encoding='utf-8') as f:
		return json.load(f)

def save_tasks(tasks):
	with open("DATE_FILE", 'w', encoding='utf-8') as f :
		json.dump(tasks, f, ensure_ascii=False, indent=4)



def command_add(content) : 
	tasks = load_tasks()
	new_id = max([i["id"] for i in tasks], default = 0) +1
	tasks.append({"id":new_id, "content": content, "done":False})
	save_tasks(tasks)
	print(f"추가됨: #{new_id} {content}")

def command_list():
	tasks = load_tasks()
	if not tasks:
		print("할일이 없습니다")
		return
	
	print("======할일 목록=====")
	for i in tasks:
		check = "[x]" if i["done"] else "[ ]"
		print(f"{check} #{i['id']} {i['content']}")

def command_done(task_id):
	tasks = load_tasks()
	for i in tasks :
		if i['id'] == task_id:
			i["done"] = True
			save_tasks(tasks)
			print(f"완료 처리 : #{task_id} {i['content']}")
			return
	print(f"#{task_id}를 찾을 수 없습니다")

def command_remove(task_id):
	tasks = load_tasks()
	#삭제하는게 아니라 삭제하기로 선택된 번호만 저장을 하지 않음 (!= 사용)
	new_tasks = [i for i in tasks if i['id'] != task_id]
	if len(new_tasks) == len(tasks):
		print(f"#{task_id}를 찾을 수 없습니다")
		return
	save_tasks(new_tasks)
	print(f"#{task_id} 삭제 완료")


def main():
	
#규칙 선언
	parser = argparse.ArgumentParser(description = "간단한 할일 관리 CLI")
	subparsers = parser.add_subparsers(dest = "command")

	p_add = subparsers.add_parser("add", help="할일 추가")
	p_add.add_argument("content", help="할일 내용")

	subparsers.add_parser("list", help="할일 목록 보기")		#list라는 메뉴(방)만 만들어 둠 (뒤에 따라올 바구니 필요 없음)

	p_done = subparsers.add_parser("done", help="할일을 완료로 표시")	#done이라는 메뉴(방)를 만들고
	p_done.add_argument("id", type=int, help="할일 id")		#그 뒤에 꼭 숫자가 따라와야 하니까 id 바구니(Argument)를 추가해 둠!

	p_remove = subparsers.add_parser("remove", help="할일 삭제")
	p_remove.add_argument("id", type=int, help="할일 id")

#실제 실행
	args = parser.parse_args()

	if args.command == "add":
		command_add(args.content)
	elif args.command == "list":
		command_list()
	elif args.command == "done":
		command_done(args.id)
	elif args.command == "remove":
		command_remove(args.id)
	else:
		parser.print_help()


if __name__ == "__main__":
    main()