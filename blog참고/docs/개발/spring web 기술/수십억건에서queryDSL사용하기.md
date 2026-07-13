## 꼭 프로젝트에 적용해보자.
내가 직접 유투브 보고 요약한것보다......   AI가 2020 QueryDSL 수십억건에서  사용하기 배민에 대해 알고있는 내용 요약하는게 더 좋은듯
복붙해서   잘 정리해달라고 하자 
다만 알아두자 ... 이건 대용량에서 이렇게 하면 좋다는 내용 
OLTP에서 억지로 적용 안해도 되는 부분이 있는지는 생각해보기 
join 등이야  그때그때 적용하고 문제생기면 그때그때보는거지만    repositoryCustom,impl은 어떻게 하라는거지?  (상속/구현 구조 탈피)  직접 적용해보자 



## 상속/구현 구조 탈피 
queryDSL에서는  RepositoryCustom, RepositoryCustomImpl 매번 만들기 귀찮. 
JPAQueryFactory만 있으면  상속 안해도 됨 (별도 조회 전용 Repository 클래스에서 JPAQueryFactory 직접 주입해서 사용)
동적쿼리에서  BooleanBuilder 대신 BooleanExpression 사용하면 조건이 null 반환 시 where 절에서 자동으로 제거됨


## queryDSL exists 금지
DB의 exists는  count쿼리와 다르게   첫번째 데이터가 있으면 실행이 멈춰서 빠르지만
(구버전) queryDSL의 exists()는 내부적으로 fetchCount() 사용    return fetchCount() > 0     매칭되는 행을 전부 세느라(count) 속도 느림 
exists는 직접 구현하기  =>  return selectOne().from(...).where(...).fetchFirst() != null  
(fetchFirst()는 limit 1로 첫 행만 조회, 데이터가 없으면 null 반환)

※ 참고: fetchCount() / fetchResults()는 QueryDSL 5.0부터 deprecated. 위 fetchFirst() 방식이 현재도 권장되는 대안.


##   join 묵시적 사용 X  명시적 Join 
묵시적 join은  크로스 join 문제 발생,  명시적으로 inner join 시도

## Entity보다는 DTO    
Entity보다는 DTO 사용하기.  특히 result 개수가 많을 때 DTO로 직접 가져오기   
기본적으로 JPA 의 장점을 이용하려면 entity조회후 service 레이어에서 DTO로 반환 후 controller에 넘겨주는거 OK.
다만 성능에 문제가 있다면 repository 에서 가져올 때 애초에 DTO로 가져오는거 고려.  
stream.map 이 나쁜 건 아님 (10건정도에서.   단 N+1이 발생하는지는 확인 )



## GROUP BY 최적화 (※ MySQL 5.7 이하 기준)
(구버전 MySQL) GROUP BY 시 내부적으로 자동정렬 시도 => 성능 느림
ORDER BY NULL을 하면 자동정렬 시도 X (정렬 비용 제거)
근데 queryDSL에서는 ORDER BY NULL을 직접 지원 X
=> OrderSpecifier를 사용하거나 커스텀 클래스(커스텀 함수)를 만들어서 order by null이 동작하도록 명시
( MySQL 8.0부터는 GROUP BY 암묵적 정렬이 제거되어 이 처리 불필요 )


## JPQL은 FROM 서브쿼리 지원X
서브쿼리아니어도 join으로 해결 
or  SELECT 후 IN 절로 우회 


## 여러 데이터 변경
여러데이터일 때는 더티체킹보다는 bulk 연산하기    (더티체킹은 기본적으로 1개씩 update)
대용량 인서트는 jpa보다는  JDBC template 등  다른 방법 고려 










