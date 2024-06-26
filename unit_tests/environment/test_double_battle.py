from unittest.mock import MagicMock

from poke_env.environment import DoubleBattle, Pokemon


def test_battle_request_parsing(example_doubles_request):
    logger = MagicMock()
    battle = DoubleBattle("tag", "username", logger, gen=8)

    battle.parse_request(example_doubles_request)
    assert len(battle.team) == 6

    pokemon_names = set(map(lambda pokemon: pokemon.species, battle.team.values()))
    assert "thundurus" in pokemon_names
    assert "raichualola" in pokemon_names
    assert "maractus" in pokemon_names
    assert "zamazentacrowned" in pokemon_names

    zamazenta = battle.get_pokemon("p1: Zamazenta")
    zamazenta_moves = zamazenta.moves
    assert (
        len(zamazenta_moves) == 4
        and "closecombat" in zamazenta_moves
        and "crunch" in zamazenta_moves
        and "psychicfangs" in zamazenta_moves
        and "behemothbash" in zamazenta_moves
    )


def test_battle_request_parsing_and_interactions(example_doubles_request):
    logger = MagicMock()
    battle = DoubleBattle("tag", "username", logger, gen=8)

    battle.parse_request(example_doubles_request)
    mr_rime, klinklang = battle.active_pokemon
    (
        my_first_active,
        my_second_active,
        their_first_active,
        their_second_active,
    ) = battle.all_active_pokemons
    assert my_first_active == mr_rime and my_second_active == klinklang
    assert their_first_active is None and their_second_active is None
    assert isinstance(mr_rime, Pokemon)
    assert isinstance(klinklang, Pokemon)
    assert battle.get_pokemon("p1: Mr. Rime") == mr_rime
    assert battle.get_pokemon("p1: Klinklang") == klinklang

    assert set(battle.available_moves[0]) == set(
        battle.active_pokemon[0].moves.values()
    )
    assert set(battle.available_moves[1]) == set(
        battle.active_pokemon[1].moves.values()
    )

    assert len(battle.available_switches) == 2
    assert all(battle.can_dynamax)
    assert not any(battle.can_z_move)
    assert not any(battle.can_mega_evolve)
    assert not any(battle.trapped)
    assert not any(battle.force_switch)
    assert not any(battle.maybe_trapped)

    mr_rime.boosts = {
        "accuracy": -2,
        "atk": 1,
        "def": -6,
        "evasion": 4,
        "spa": -4,
        "spd": 2,
        "spe": 3,
    }
    klinklang.boosts = {
        "accuracy": -6,
        "atk": 6,
        "def": -1,
        "evasion": 1,
        "spa": 4,
        "spd": -3,
        "spe": 2,
    }

    battle.clear_all_boosts()

    cleared_boosts = {
        "accuracy": 0,
        "atk": 0,
        "def": 0,
        "evasion": 0,
        "spa": 0,
        "spd": 0,
        "spe": 0,
    }

    assert mr_rime.boosts == cleared_boosts
    assert klinklang.boosts == cleared_boosts

    assert battle.active_pokemon == [mr_rime, klinklang]
    battle.parse_message(["", "swap", "p1b: Klinklang", ""])
    assert battle.active_pokemon == [klinklang, mr_rime]

    battle.switch("p2a: Milotic", "Milotic, L50, F", "48/48")
    battle.switch("p2b: Tyranitar", "Tyranitar, L50, M", "48/48")

    milotic, tyranitar = battle.opponent_active_pokemon
    assert milotic.species == "milotic"
    assert tyranitar.species == "tyranitar"

    assert all(battle.opponent_can_dynamax)


def test_get_possible_showdown_targets(example_doubles_request):
    logger = MagicMock()
    battle = DoubleBattle("tag", "username", logger, gen=8)

    battle.parse_request(example_doubles_request)
    mr_rime, klinklang = battle.active_pokemon
    psychic = mr_rime.moves["psychic"]
    slackoff = mr_rime.moves["slackoff"]

    battle.switch("p2b: Tyranitar", "Tyranitar, L50, M", "48/48")
    assert battle.get_possible_showdown_targets(psychic, mr_rime) == [-2, 2]

    battle.switch("p2a: Milotic", "Milotic, L50, F", "48/48")
    assert battle.get_possible_showdown_targets(psychic, mr_rime) == [-2, 1, 2]
    assert battle.get_possible_showdown_targets(slackoff, mr_rime) == [0]
    assert battle.get_possible_showdown_targets(psychic, mr_rime, dynamax=True) == [
        1,
        2,
    ]
    assert battle.get_possible_showdown_targets(slackoff, mr_rime, dynamax=True) == [0]


def test_to_showdown_target(example_doubles_request):
    logger = MagicMock()
    battle = DoubleBattle("tag", "username", logger, gen=8)

    battle.parse_request(example_doubles_request)
    mr_rime, klinklang = battle.active_pokemon
    opp1, opp2 = battle.opponent_active_pokemon
    psychic = mr_rime.moves["psychic"]
    slackoff = mr_rime.moves["slackoff"]

    assert battle.to_showdown_target(psychic, klinklang) == -2
    assert battle.to_showdown_target(psychic, opp1) == 0
    assert battle.to_showdown_target(slackoff, mr_rime) == 0
    assert battle.to_showdown_target(slackoff, None) == 0


def test_end_illusion():
    logger = MagicMock()
    battle = DoubleBattle("tag", "username", logger, gen=8)
    battle.player_role = "p2"

    battle.switch("p2a: Celebi", "Celebi", "100/100")
    battle.switch("p2b: Ferrothorn", "Ferrothorn, M", "100/100")
    battle.switch("p1a: Pelipper", "Pelipper, F", "100/100")
    battle.switch("p1b: Kingdra", "Kingdra, F", "100/100")

    battle.end_illusion("p2a: Zoroark", "Zoroark, M")
    zoroark = battle.team["p2: Zoroark"]
    celebi = battle.team["p2: Celebi"]
    ferrothorn = battle.team["p2: Ferrothorn"]
    assert zoroark in battle.active_pokemon
    assert ferrothorn in battle.active_pokemon
    assert celebi not in battle.active_pokemon


def test_one_mon_left_in_double_battles_results_in_available_move_in_the_correct_slot():
    request = {
        "active": [
            {
                "moves": [
                    {
                        "move": "Ally Switch",
                        "id": "allyswitch",
                        "pp": 18,
                        "maxpp": 24,
                        "target": "self",
                        "disabled": False,
                    }
                ]
            },
            {
                "moves": [
                    {
                        "move": "Recover",
                        "id": "recover",
                        "pp": 4,
                        "maxpp": 8,
                        "target": "self",
                        "disabled": False,
                    },
                    {
                        "move": "Haze",
                        "id": "haze",
                        "pp": 46,
                        "maxpp": 48,
                        "target": "all",
                        "disabled": False,
                    },
                ]
            },
        ],
        "side": {
            "name": "DisplayPlayer 1",
            "id": "p1",
            "pokemon": [
                {
                    "ident": "p1: Cresselia",
                    "details": "Cresselia, F",
                    "condition": "0 fnt",
                    "active": True,
                    "stats": {
                        "atk": 145,
                        "def": 350,
                        "spa": 167,
                        "spd": 277,
                        "spe": 206,
                    },
                    "moves": ["allyswitch"],
                    "baseAbility": "levitate",
                    "item": "rockyhelmet",
                    "pokeball": "pokeball",
                    "ability": "levitate",
                    "commanding": False,
                    "reviving": False,
                    "teraType": "Psychic",
                    "terastallized": "",
                },
                {
                    "ident": "p1: Milotic",
                    "details": "Milotic, F",
                    "condition": "386/394",
                    "active": True,
                    "stats": {
                        "atk": 112,
                        "def": 194,
                        "spa": 236,
                        "spd": 383,
                        "spe": 199,
                    },
                    "moves": ["recover", "haze"],
                    "baseAbility": "marvelscale",
                    "item": "leftovers",
                    "pokeball": "pokeball",
                    "ability": "marvelscale",
                    "commanding": False,
                    "reviving": False,
                    "teraType": "Water",
                    "terastallized": "Water",
                },
            ],
        },
        "rqid": 16,
    }

    battle = DoubleBattle("tag", "username", MagicMock(), gen=9)
    battle.parse_message(["", "player", "p1", "username", "102", ""])
    battle.parse_message(["", "player", "p2", "username2", "102", ""])

    battle.parse_message(["", "switch", "p1a: Milotic", "Milotic, F", "394/394"])
    battle.parse_message(["", "switch", "p1b: Cresselia", "Cresselia, F", "444/444"])
    battle.parse_message(["", "switch", "p2a: Vaporeon", "Vaporeon, F", "100/100"])
    battle.parse_message(["", "switch", "p2b: Pelipper", "Pelipper, M", "100/100"])
    battle.parse_message(["", "turn", "1"])

    battle.parse_request(request)
    battle.parse_message(
        ["", "swap", "p1b: Cresselia", "0", "[from] move: Ally Switch"]
    )

    print(battle.available_moves)
    print(battle.active_pokemon)

    assert battle.available_moves[0] == []
    assert [m.id for m in battle.available_moves[1]] == ["recover", "haze"]
    assert battle.active_pokemon[0] is None
    assert battle.active_pokemon[1].species == "milotic"
