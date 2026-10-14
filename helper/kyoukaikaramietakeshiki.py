# Notes:
import sys
import json
from pathlib import Path
from typing import Any

# Add project root to sys.path (find the directory containing db_structs.py)
_root = Path(__file__).resolve().parent
while _root.parent != _root:
    if (_root / "db_structs.py").exists():
        if str(_root) not in sys.path:
            sys.path.append(str(_root))
        break
    _root = _root.parent

from db_structs import (
    Medium,
    Circle,
    Event,
    EventGroup,
    Source,
    ReliabilityTypes,
    OriginTypes,
    Location,
)

RT, OT = ReliabilityTypes, OriginTypes

PATH_HELPER = Path(__file__).parent
PATH_EVENT_GROUP = PATH_HELPER.parent
PATH_MEDIA = PATH_EVENT_GROUP / "media"


def retrieve_circles(event_name: str) -> list[Circle]:
    """Retrieve circles of given event. In the circle file has not been created, execute the creation script first."""
    circles_json_path = PATH_HELPER / event_name / "circles.json"
    if not circles_json_path.exists():
        print(
            f"Circle file for {event_name} not found, running the creation script ..."
        )
        creation_script_path = PATH_HELPER / event_name / "main.py"
        if not creation_script_path.exists():
            raise FileNotFoundError(
                f"Creation script for {event_name} not found at {creation_script_path}"
            )
        # Import main() from the creation script and execute
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            f"{event_name}.main", creation_script_path
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "main"):
                module.main()

        if not circles_json_path.exists():
            raise FileNotFoundError(
                f"Creation script {creation_script_path} failed to create {circles_json_path}"
            )

    with circles_json_path.open("r", encoding="utf-8") as f:
        circles_raw = json.load(f)
    return [Circle.load_from_json(c) for c in circles_raw]


if __name__ == "__main__":
    events: list[Event] = []
    disabled_events: list[int | str] = []
    thwikicc = "https://thwiki.cc/%E5%A2%83%E7%95%8C%E6%89%80%E8%A7%81%E5%88%B0%E7%9A%84%E5%A4%96%E7%95%8C"

    i = 1  # ==== kyoukaikaramietakeshiki ====
    if i not in disabled_events:
        event_name = f"kyoukaikaramietakeshiki{i}"
        print(f"Processing {event_name} ...")

        media_ = [
            Medium(
                "01_top02.jpg",
                [
                    Source(
                        "https://web.archive.org/web/20100325135714/http://kyoukai.warabies.com/",
                        (RT.Reliable, OT.Official),
                    ),
                ],
                comments="Illustration: 彩社長(極彩色)",
            ),
            Medium(
                "01_境界所见到的外界顶图1.jpg",
                [Source(thwikicc, (RT.Likely, OT.External))],
            ),
            Medium(
                "https://web.archive.org/web/20250112160330/http://www.green.dti.ne.jp/maisan/gensoukyou/image/kyoukaikaramietakeshiki.pdf",
                [
                    Source(
                        "https://web.archive.org/web/20250112160330/http://www.green.dti.ne.jp/maisan/gensoukyou/image/kyoukaikaramietakeshiki.pdf",
                        (RT.Reliable, OT.OfficialExt),
                    )
                ],
            ),
            Medium(
                "https://web.archive.org/web/20100911064150/http://kyoukai.warabies.com/kyoukai.pdf",
                [
                    Source(
                        "https://web.archive.org/web/20100911064150/http://kyoukai.warabies.com/kyoukai.pdf",
                        (RT.Reliable, OT.Official),
                    )
                ],
            ),
            # Medium("", [Source("", (RT.Reliable, OT.Official))]),
        ]
        locations = [
            Location(
                coordinates=(35.655153, 139.7607689),
                address="Japan, 〒105-7501 Tokyo, Minato City, Kaigan, 1 Chome−7−1 東京ポートシティ竹芝オフィスタワ",
                comments=None,
                description="東京都立産業貿易センター 浜松町館",
                sources=[
                    Source(
                        "https://web.archive.org/web/20100325135714/http://kyoukai.warabies.com/",
                        (RT.Reliable, OT.Official),
                    ),
                    Source(
                        "Changed location: https://web.archive.org/web/20100325135714/http://kyoukai.warabies.com/",
                        (RT.Reliable, OT.Official),
                    ),
                ],
                imageUrl="https://lh3.googleusercontent.com/gps-cs-s/AHRPTWmihIGbPitN7h8Vc_sXo8I679FTgrlkYst2LWaAy_Wl45MDqMaFnozSO4Y2Vud8h07FgRpXdq_CPW3IWnFwj-AyKuJ0L7ShZyQ41TQcBAFNOouYZR3jFZXxn_SQsgsK-FST-5JK8g=w408-h544-k-no",
                url="https://maps.app.goo.gl/ZF8XaGQinUTwnNMw6",
            ),
            Location(
                coordinates=(35.5352689, 139.6991018),
                address="66-20 Horikawacho, Saiwai Ward, Kawasaki, Kanagawa 212-0013, Japan",
                description="川崎市産業振興会館",
                sources=[
                    Source(
                        "https://web.archive.org/web/20100222165630/http://kyoukai.warabies.com/",
                        (RT.Reliable, OT.Official),
                    )
                ],
                comments="Original location, later moved to 東京都立産業貿易センター 浜松町館.",
                imageUrl="https://lh3.googleusercontent.com/gps-cs-s/AHRPTWnWztJ2ppoe3w-RXwZKQrT3vkgEbIN62FGlT7NE7zuGU7eM3ofV9HW_XPJIhG_gdXsqJye8REtNEDXEuXtA4hNE6eBFPNp2sgCSTD6dXYj3of4yaxjAaBFGG8WNY2Pr-rM431y9Sf2f9Zg=s0?imgmax=0",
                url="https://maps.app.goo.gl/GBVsEToTAegdTRpK8",
            ),
        ]
        event = Event(
            aliases=["境界から視えた外界", "Kyoukai kara Mieta Keshiki"],
            dates="2010.11.28",
            circles=[],
            media=media_,
            sources=[
                Source(
                    "Date: https://web.archive.org/web/20100222165630/http://kyoukai.warabies.com/",
                    (RT.Reliable, OT.Official),
                ),
                Source(
                    "Participating circles: https://web.archive.org/web/20250112160330/http://www.green.dti.ne.jp/maisan/gensoukyou/image/kyoukaikaramietakeshiki.pdf",
                    (RT.Reliable, OT.OfficialExt),
                ),
            ],
            locations=locations,
            description=None,
            # comments=None,
            last_edited="2026.10.13",
        )

        # Retrieve circles
        event.circles = retrieve_circles(event_name)
        events.append(event)

    i = 2  # ==== kyoukaikaramietakeshiki2 ====
    if i not in disabled_events:
        event_name = f"kyoukaikaramietakeshiki{i}"
        print(f"Processing {event_name} ...")

        media_ = [
            Medium(
                "02_top03.jpg",
                [
                    Source(
                        "https://web.archive.org/web/20121124122035/http://kyoukai.biz/",
                        (ReliabilityTypes.Reliable, OriginTypes.Official),
                    )
                ],
                comments="Illustration:はふり(Lapin Asile)",
            ),
            # Medium("", [Source("", (RT.Reliable, OT.Official))]),
            # Medium("", [Source("", (RT.Reliable, OT.Official))]),
            # Medium("", [Source("", (RT.Reliable, OT.Official))]),
        ]
        locations = [
            Location(
                coordinates=(35.655153, 139.7607689),
                address="Japan, 〒105-7501 Tokyo, Minato City, Kaigan, 1 Chome−7−1 東京ポートシティ竹芝オフィスタワ",
                comments=None,
                description="東京都港区海岸1-7-8東京都立産業貿易センター　浜松町館",
                sources=[
                    Source(
                        "https://www.pixiv.net/event_detail.php?event_id=2084",
                        (RT.Reliable, OT.OfficialExt),
                    ),
                ],
                imageUrl="https://lh3.googleusercontent.com/gps-cs-s/AHRPTWmihIGbPitN7h8Vc_sXo8I679FTgrlkYst2LWaAy_Wl45MDqMaFnozSO4Y2Vud8h07FgRpXdq_CPW3IWnFwj-AyKuJ0L7ShZyQ41TQcBAFNOouYZR3jFZXxn_SQsgsK-FST-5JK8g=w408-h544-k-no",
                url="https://maps.app.goo.gl/ZF8XaGQinUTwnNMw6",
            ),
        ]
        event = Event(
            aliases=["境界から視えた外界-廻-", "Kyoukai kara Mieta Keshiki -Mawari-"],
            dates="2012.09.09",
            circles=[],
            media=media_,
            sources=[
                Source(
                    "Date: https://www.pixiv.net/event_detail.php?event_id=2084",
                    (ReliabilityTypes.Reliable, OriginTypes.OfficialExt),
                ),
                Source(
                    "Participating circles: https://web.archive.org/web/20130608043923/http://kyoukai.biz:80/list01.htm",
                    (ReliabilityTypes.Reliable, OriginTypes.Official),
                ),
            ],
            locations=locations,
            description=None,
            # comments=None,
            last_edited="2026.10.13",
        )

        # Retrieve circles
        event.circles = retrieve_circles(event_name)
        events.append(event)

    i = 3  # ==== kyoukaikaramietakeshiki3 ====
    if i not in disabled_events:
        event_name = f"kyoukaikaramietakeshiki{i}"
        print(f"Processing {event_name} ...")

        media_ = [
            Medium(
                "03_top04.jpg",
                [
                    Source(
                        "https://web.archive.org/web/20140518000247/http://kyoukai.biz/",
                        (ReliabilityTypes.Reliable, OriginTypes.Official),
                    )
                ],
                comments="Illustration:ランコの姉(豚乙女)",
            ),
            Medium(
                "03_top05.jpg",
                [
                    Source(
                        "https://web.archive.org/web/20140812085832/http://kyoukai.biz/",
                        (ReliabilityTypes.Reliable, OriginTypes.Official),
                    )
                ],
                comments="Illustration:桜庭友紀(PERSONAL COLOR)",
            ),
            Medium(
                "03_20150221_haichi.png",
                [
                    Source(
                        "https://web.archive.org/web/20150728094209/http://project-d.biz/tohosaiji/circle_list.html",
                        (RT.Reliable, OT.Official),
                    )
                ],
            ),
            # Medium("", [Source("", (RT.Reliable, OT.Official))]),
            # Medium("", [Source("", (RT.Reliable, OT.Official))]),
        ]
        locations = [
            Location(
                coordinates=(35.5587817, 139.7240667),
                address="1 Chome-20-20 Minamikamata, Ota City, Tokyo 144-0035, Japan",
                description="東京都東京都大田区南蒲田１−２０−２０大田区産業プラザPiO",
                sources=[
                    Source(
                        "https://www.pixiv.net/event_detail.php?event_id=4382",
                        (ReliabilityTypes.Reliable, OriginTypes.OfficialExt),
                    )
                ],
                # comments=None,
                imageUrl="https://lh3.googleusercontent.com/gps-cs-s/AHRPTWlSopXAxX4zYII19vbdI4rX0w5RiVyPdD_3T-rcKAI3NBfzD7cKS2HEXWrr_JXATLT3BXULla2lC3oHidDik9oIlyt_6fS4t9y2wbW_lLHAvuil4Cw0WsOtevHY2sumWk6a1Mp8Hg=s0?imgmax=0",
                url="https://maps.app.goo.gl/mSxwaUchFHGpFwBf9",
            ),
        ]
        event = Event(
            aliases=["境界から視えた外界-結-", "Kyoukai kara Mieta Keshiki -Musubu-"],
            dates="2015.02.21",
            circles=[],
            media=media_,
            sources=[
                Source(
                    "Date, alias transliteration: https://web.archive.org/web/20140518000247/http://kyoukai.biz/",
                    (RT.Reliable, OT.Official),
                ),
                Source(
                    "Participating circles: https://web.archive.org/web/20150728094209/http://project-d.biz/tohosaiji/circle_list.html",
                    (ReliabilityTypes.Reliable, OriginTypes.Official),
                ),
            ],
            locations=locations,
            description="Part of the 2015 東方合同祭事参 venue: https://web.archive.org/web/20150224200242/http://project-d.biz/tohosaiji/event.html",
            # comments=None,
            last_edited="2026.10.14",
        )

        # Retrieve circles
        event.circles = retrieve_circles(event_name)
        events.append(event)

    i = 4  # ==== kyoukaikaramietakeshiki4 ====
    if i not in disabled_events:
        event_name = f"kyoukaikaramietakeshiki{i}"
        print(f"Processing {event_name} ...")

        media_ = [
            Medium(
                "04_top06.jpg",
                [
                    Source(
                        "https://web.archive.org/web/20170425073255/http://kyoukai.biz/",
                        (ReliabilityTypes.Reliable, OriginTypes.Official),
                    )
                ],
                comments="Illustration:鳥居すみ(airdrop)",
            ),
            Medium(
                "04_20170326daiten.jpg",
                [
                    Source(
                        "https://web.archive.org/web/20170504223846/http://project-d.biz/tohosaiji/circle_list.html",
                        (RT.Reliable, OT.Official),
                    )
                ],
            ),
            # Medium("", [Source("", (RT.Reliable, OT.Official))]),
            # Medium("", [Source("", (RT.Reliable, OT.Official))]),
        ]
        locations = [
            Location(
                coordinates=(35.5587817, 139.7240667),
                address="1 Chome-20-20 Minamikamata, Ota City, Tokyo 144-0035, Japan",
                description="東京都大田区南蒲田１丁目２０−２０大田区産業プラザPiO",
                sources=[
                    Source(
                        "https://www.pixiv.net/event_detail.php?event_id=5852",
                        (ReliabilityTypes.Reliable, OriginTypes.OfficialExt),
                    )
                ],
                # comments=None,
                imageUrl="https://lh3.googleusercontent.com/gps-cs-s/AHRPTWlSopXAxX4zYII19vbdI4rX0w5RiVyPdD_3T-rcKAI3NBfzD7cKS2HEXWrr_JXATLT3BXULla2lC3oHidDik9oIlyt_6fS4t9y2wbW_lLHAvuil4Cw0WsOtevHY2sumWk6a1Mp8Hg=s0?imgmax=0",
                url="https://maps.app.goo.gl/mSxwaUchFHGpFwBf9",
            ),
        ]
        event = Event(
            aliases=["境界から視えた外界-至-", "Kyoukai kara Mieta Keshiki -Itaru-"],
            dates="2017.03.26",
            circles=[],
            media=media_,
            sources=[
                Source(
                    "Date: https://web.archive.org/web/20170425073255/http://kyoukai.biz/",
                    (ReliabilityTypes.Reliable, OriginTypes.Official),
                ),
                Source(
                    "Participating circles: https://web.archive.org/web/20170504223846/http://project-d.biz/tohosaiji/circle_list.html",
                    (ReliabilityTypes.Reliable, OriginTypes.Official),
                ),
            ],
            locations=locations,
            description="Part of the 2017 東方合同祭事 venue: https://web.archive.org/web/20170504223846/http://project-d.biz/tohosaiji/circle_list.html",
            # comments=None,
            last_edited="2026.10.14",
        )

        # Retrieve circles
        event.circles = retrieve_circles(event_name)
        events.append(event)

    # i =   # ==== kyoukaikaramietakeshiki ====
    # if i not in disabled_events:
    #     event_name = f"kyoukaikaramietakeshiki{i}"
    #     print(f"Processing {event_name} ...")

    #     media_ = [
    #         # Medium("", [Source("", (RT.Reliable, OT.Official))]),
    #         # Medium("", [Source("", (RT.Reliable, OT.Official))]),
    #         # Medium("", [Source("", (RT.Reliable, OT.Official))]),
    #     ]
    #     locations = [
    #         # Location(
    #         #     coordinates=(,),
    #         #     address="",
    #         #     description="",
    #         #     sources=[Source("", (RT.Reliable, OT.Official))],
    #         #     # comments=None,
    #         #     imageUrl="",
    #         #     url="",
    #         # ),
    #     ]
    #     event = Event(
    #         aliases=,
    #         dates="",
    #         circles=[],
    #         media=media_,
    #         sources=[
    #             # Source(f"Date: {}", (RT.Reliable, OT.Official)),
    #             # Source("Participating circles: ", (RT.Reliable, OT.Official)),
    #         ],
    #         locations=locations,
    #         description=None,
    #         # comments=None,
    #         last_edited="2026.10.13",
    #     )

    #     # Retrieve circles
    #     # event.circles = retrieve_circles(event_name)
    #     events.append(event)

    # ==== event group ====
    media = [
        Medium(
            "eg_banner.jpg",
            [
                Source(
                    "https://web.archive.org/web/20121124122035/http://kyoukai.biz/",
                    (ReliabilityTypes.Reliable, OriginTypes.Official),
                )
            ],
        ),
        # Medium("",
        #        [Source("", (RT.Reliable, OT.Official))]),
        # Medium("",
        #        [Source("", (RT.Reliable, OT.Official))]),
    ]
    links = [
        "http://kyoukai.warabies.com/",
        "https://kyoukai.biz/",
        "https://x.com/kyoukai_hifuu",
        "https://yumemichi.koromu-toho.com/",
    ]

    event_group = EventGroup(
        aliases=[
            "境界から視えた外界",
            "Kyoukai kara Mieta Keshiki",
        ],
        events=events,
        media=media,
        links=links,
        sources=[
            # Source(
            #     "",
            #     (RT.Reliable, OT.Official),
            # ),
        ],
        comments=None,
        description=None,
        last_edited="2026.10.14",
    )

    print(f"Saving {Path(__file__).stem} database...")
    event_group.save(PATH_EVENT_GROUP, indent=None)
    print("Done")
