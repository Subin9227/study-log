import asyncio 									 								#비동기
import sys

meetings = []

async def main():																#비동기
	print("==============================")
	print("   소중한 만남 기록기 (CLI)   ")
	print("==============================")

	while True :
		print("\n>>> [1] 만남 기록하기 \n>>> [2] 전체 기록보기 \n>>> [3] 종료")
		choice = input("원하는 메뉴 번호를 입력하세요: ").strip()

		if choice == "1":
			name = input("\n 누구를 만났어요?: ").strip()
			time = input(" 언제 만났어요? (예: 2026-05-16): ").strip()
			if name and time :
				
				print("\n 데이터베이스에 저장 중입니다...")							#비동기
				await asyncio.sleep(2)											#비동기


				meetings.append({"name":name, "time":time})
				print(f"✅ {name}님과의 만남이 기록되었습니다.")
			else :
				print("❌ 이름과 시간을 모두 입력해주세요.")

		elif choice == "2":
			if not meetings:
				print("\n 아직 기록된 만남이 없습니다")
			else :
				print("\n ----- 만남 기록 리스트 -----")
				for idx, meet in enumerate(meetings, 1):
					print(f"{idx}. {meet['name']} (일시: {meet['time']}")
				print("------------------------------")

		elif choice == "3":
			print("\n 프로그램을 종료합니다.")
			sys.exit()
		
		else:
			print("❌ 올바른 번호를 선택해 주세요.")


if __name__ == "__main__":
	asyncio.run(main())															#비동기

