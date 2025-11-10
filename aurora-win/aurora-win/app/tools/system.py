async def exec(args, policy, db):
    # ! HIGH-RISK ! (일반 실행)
    # TODO: subprocess.run(args.get("command"))
    return {"return_code": 0}

async def exec_limited(args, policy, db):
    # ! HIGH-RISK ! (제한된 실행 - 예: scripts/signed_ps/ 내)
    # TODO: 서명된 스크립트인지 확인 후 실행
    return {"return_code": 0}