from flask import Flask, render_template, request
import heapq
from pathlib import Path

import pandas as pd


app = Flask(__name__)


# ==========================================
# 1. 엑셀 데이터 불러오기
# ==========================================

DATA_PATH = Path(__file__).parent / "data" / "stations.xlsx"
WEIGHT_COLUMNS = {
    "time": "시간(초)",
    "distance": "거리(미터)",
    "cost": "비용(원)",
}

# 제공받은 노선도 이미지(928 x 642) 위에서 각 역을 강조하기 위한 좌표다.
STATION_POSITIONS = {
    "101": (82, 334), "102": (83, 388), "103": (82, 448), "104": (84, 506),
    "105": (82, 566), "106": (112, 609), "107": (176, 609), "108": (226, 610),
    "109": (273, 610), "110": (337, 609), "111": (402, 610), "112": (466, 609),
    "113": (543, 609), "114": (572, 561), "115": (571, 507), "116": (572, 428),
    "117": (572, 386), "118": (563, 320), "119": (468, 302), "120": (402, 303),
    "121": (339, 303), "122": (274, 303), "123": (175, 302),
    "201": (83, 254), "202": (84, 204), "203": (84, 157), "204": (83, 108),
    "205": (85, 61), "206": (130, 61), "207": (175, 61), "208": (224, 63),
    "209": (274, 61), "210": (336, 59), "211": (468, 60), "212": (529, 59),
    "213": (600, 60), "214": (663, 64), "215": (720, 63), "216": (776, 61),
    "217": (872, 61),
    "301": (175, 109), "302": (174, 159), "303": (175, 206), "304": (175, 256),
    "305": (178, 387), "306": (175, 449), "307": (177, 507), "308": (177, 566),
    "401": (131, 507), "402": (225, 507), "403": (273, 507), "404": (337, 506),
    "405": (402, 507), "406": (467, 506), "407": (520, 506), "408": (614, 507),
    "409": (662, 507), "410": (721, 507), "411": (775, 507), "412": (775, 428),
    "413": (775, 388), "414": (776, 318), "415": (775, 254), "416": (777, 206),
    "417": (775, 121),
    "501": (273, 108), "502": (274, 159), "503": (273, 206), "504": (273, 254),
    "505": (271, 387), "506": (274, 447), "507": (274, 566),
    "601": (340, 209), "602": (338, 255), "603": (339, 386), "604": (404, 428),
    "605": (466, 429), "606": (519, 429), "607": (612, 428), "608": (663, 428),
    "609": (721, 429), "610": (839, 429), "611": (873, 388), "612": (870, 318),
    "613": (870, 254), "614": (874, 206), "615": (873, 161), "616": (821, 120),
    "617": (720, 121), "618": (662, 124), "619": (600, 123), "620": (529, 122),
    "621": (467, 122), "622": (403, 123),
    "701": (402, 206), "702": (466, 206), "703": (529, 206), "704": (600, 204),
    "705": (664, 206), "706": (723, 206), "707": (826, 206),
    "801": (609, 610), "802": (659, 609), "803": (662, 561), "804": (664, 387),
    "805": (663, 320), "806": (662, 254),
    "901": (468, 561), "902": (468, 387), "903": (468, 254), "904": (467, 158),
}

data = pd.read_excel(DATA_PATH)

stations = sorted(
    set(data["출발역"].astype(str))
    | set(data["도착역"].astype(str))
)


# ==========================================
# 2. 지하철 그래프 만들기
# ==========================================

graph = {}
edge_info = {}

for _, row in data.iterrows():
    start = str(row["출발역"])
    end = str(row["도착역"])

    graph.setdefault(start, [])
    graph.setdefault(end, [])

    if end not in graph[start]:
        graph[start].append(end)

    if start not in graph[end]:
        graph[end].append(start)

    # 엑셀에 기록된 구간은 양방향 이동이 가능하도록 한 번만 저장한다.
    # 중복 구간이 있더라도 기존 코드와 동일하게 첫 번째 행을 사용한다.
    edge_info.setdefault((start, end), row)
    edge_info.setdefault((end, start), row)


# ==========================================
# 3. 두 역 사이의 구간 정보 찾기
# ==========================================

def get_edge_info(start, end):
    """두 역 사이의 시간, 거리, 비용 정보를 반환한다."""
    return edge_info.get((start, end))


# ==========================================
# 4. 최적 경로 찾기 - 다익스트라
# ==========================================

def find_best_route(start, end, weight_column):
    """
    weight_column 기준으로 가장 좋은 경로를 찾는다.

    예:
    시간(초)  → 가장 빠른 길
    거리(미터) → 가장 짧은 길
    비용(원)  → 가장 저렴한 길
    """

    if start not in graph or end not in graph:
        return None

    if start == end:
        return [start]

    distances = {
        station: float("inf")
        for station in graph
    }

    previous = {}

    distances[start] = 0
    queue = [(0, start)]

    while queue:
        current_weight, current = heapq.heappop(queue)

        if current_weight > distances[current]:
            continue

        if current == end:
            break

        for next_station in graph[current]:

            edge = get_edge_info(current, next_station)

            if edge is None:
                continue

            weight = float(edge[weight_column])
            new_weight = current_weight + weight

            if new_weight < distances[next_station]:
                distances[next_station] = new_weight
                previous[next_station] = current

                heapq.heappush(
                    queue,
                    (new_weight, next_station)
                )

    if end not in previous:
        return None

    path = []
    current = end

    while current != start:
        path.append(current)
        current = previous[current]

    path.append(start)
    path.reverse()

    return path


# ==========================================
# 5. 경로의 총 시간 / 거리 / 비용 계산
# ==========================================

def calculate_route_info(route):
    """선택된 경로의 총 시간, 거리, 비용을 계산한다."""

    total_time = 0
    total_distance = 0
    total_cost = 0

    for i in range(len(route) - 1):
        start = route[i]
        end = route[i + 1]

        edge = get_edge_info(start, end)

        if edge is None:
            continue

        total_time += float(edge["시간(초)"])
        total_distance += float(edge["거리(미터)"])
        total_cost += float(edge["비용(원)"])

    return total_time, total_distance, total_cost


def get_route_segments(route):
    """경로를 화면에 표시할 구간별 정보로 변환한다."""

    segments = []

    for order, (start, end) in enumerate(zip(route, route[1:]), start=1):
        edge = get_edge_info(start, end)
        if edge is None:
            continue

        segments.append({
            "order": order,
            "start": start,
            "end": end,
            "time": float(edge["시간(초)"]),
            "distance": float(edge["거리(미터)"]),
            "cost": float(edge["비용(원)"]),
            "start_position": STATION_POSITIONS.get(start),
            "end_position": STATION_POSITIONS.get(end),
        })

    return segments


# ==========================================
# 6. 경로 기준에 따른 함수 선택
# ==========================================

def get_route_by_criteria(start, end, criteria):
    """선택한 기준에 맞는 최적 경로를 반환한다."""

    weight_column = WEIGHT_COLUMNS.get(criteria)
    if weight_column is None:
        return None

    return find_best_route(start, end, weight_column)


def get_criteria_text(criteria):
    """경로 기준을 화면에 표시할 문구로 변환한다."""

    texts = {
        "time": "가장 빠른 길",
        "distance": "가장 짧은 길",
        "cost": "가장 저렴한 길"
    }

    return texts.get(criteria, "")


# ==========================================
# 7. 메인 페이지
# ==========================================

@app.route("/")
def home():
    return render_template(
        "index.html",
        stations=stations
    )


# ==========================================
# 8. 경로 검색
# ==========================================

@app.route("/route", methods=["POST"])
def route():

    start = request.form.get("start", "")
    end = request.form.get("end", "")
    criteria = request.form.get("criteria", "")

    if (
        start not in graph
        or end not in graph
        or start == end
        or criteria not in WEIGHT_COLUMNS
    ):
        return render_template(
            "index.html",
            stations=stations,
            route_text="출발역과 도착역은 서로 다르게 선택해주세요.",
            selected_start=start,
            selected_end=end,
            selected_criteria=criteria,
            criteria_text="",
            selected_compare_criteria=None,
            total_time=0,
            total_distance=0,
            total_cost=0,
        )

    result = get_route_by_criteria(
        start,
        end,
        criteria
    )

    criteria_text = get_criteria_text(criteria)

    if result:
        route_text = " → ".join(result)

        total_time, total_distance, total_cost = (
            calculate_route_info(result)
        )
        route_segments = get_route_segments(result)

    else:
        route_text = "경로를 찾을 수 없습니다."

        total_time = 0
        total_distance = 0
        total_cost = 0
        route_segments = []

    return render_template(
        "index.html",
        route_text=route_text,
        total_time=total_time,
        total_distance=total_distance,
        total_cost=total_cost,
        stations=stations,
        selected_start=start,
        selected_end=end,
        selected_criteria=criteria,
        criteria_text=criteria_text,
        selected_compare_criteria=None,
        route_segments=route_segments,
    )


# ==========================================
# 9. 경로 비교
# ==========================================

@app.route("/compare", methods=["POST"])
def compare():

    start = request.form.get("start", "")
    end = request.form.get("end", "")
    criteria = request.form.get("criteria", "")
    compare_criteria = request.form.get("compare_criteria", "")

    if (
        start not in graph
        or end not in graph
        or start == end
        or criteria not in WEIGHT_COLUMNS
        or compare_criteria not in WEIGHT_COLUMNS
        or criteria == compare_criteria
    ):
        return render_template(
            "index.html",
            stations=stations,
            route_text="올바른 비교 기준을 선택해주세요.",
            selected_start=start,
            selected_end=end,
            selected_criteria=criteria,
            criteria_text=get_criteria_text(criteria),
            selected_compare_criteria=compare_criteria,
            total_time=0,
            total_distance=0,
            total_cost=0,
        )

    # 기준 경로
    base_route = get_route_by_criteria(
        start,
        end,
        criteria
    )

    # 비교 경로
    compare_route = get_route_by_criteria(
        start,
        end,
        compare_criteria
    )

    criteria_text = get_criteria_text(criteria)
    compare_text = get_criteria_text(compare_criteria)

    # 경로가 없는 경우
    if not base_route or not compare_route:

        return render_template(
            "index.html",
            stations=stations,
            selected_start=start,
            selected_end=end,
            selected_criteria=criteria,
            criteria_text=criteria_text,
            route_text="경로를 찾을 수 없습니다.",
            selected_compare_criteria=compare_criteria,
            total_time=0,
            total_distance=0,
            total_cost=0,
        )

    # 기준 경로 정보
    total_time, total_distance, total_cost = (
        calculate_route_info(base_route)
    )
    route_segments = get_route_segments(base_route)

    # 비교 경로 정보
    compare_total_time, compare_total_distance, compare_total_cost = (
        calculate_route_info(compare_route)
    )
    compare_route_segments = get_route_segments(compare_route)

    # 비교 결과
    time_diff = compare_total_time - total_time
    distance_diff = compare_total_distance - total_distance
    cost_diff = compare_total_cost - total_cost
    comparison_is_same = (
        time_diff == 0 and distance_diff == 0 and cost_diff == 0
    )

    route_text = " → ".join(base_route)

    return render_template(
        "index.html",
        route_text=route_text,
        total_time=total_time,
        total_distance=total_distance,
        total_cost=total_cost,
        stations=stations,
        selected_start=start,
        selected_end=end,
        selected_criteria=criteria,
        criteria_text=criteria_text,
        compare_text=compare_text,
        selected_compare_criteria=compare_criteria,
        route_segments=route_segments,
        compare_total_time=compare_total_time,
        compare_total_distance=compare_total_distance,
        compare_total_cost=compare_total_cost,
        time_diff=time_diff,
        distance_diff=distance_diff,
        cost_diff=cost_diff,
        comparison_is_same=comparison_is_same,
        compare_route_segments=compare_route_segments,
    )


# ==========================================
# 10. 서버 실행
# ==========================================

if __name__ == "__main__":
    app.run(debug=False)
