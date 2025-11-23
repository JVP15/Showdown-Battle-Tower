from poke_env.data.gen_data import GenData

class AbilityDex():
    def __init__(self):
        self.ability_dex = {}
        # Initialize GenData for generation 8
        self.gen_data = GenData.from_gen(8)
        self.pokedex = self.gen_data.pokedex

        for pokemon in self.pokedex.values():
            abilities = pokemon.get('abilities').values()

            for ability in abilities:
                ability_key = ability.lower().replace(" ", "")

                if ability_key not in self.ability_dex.keys():
                    self.ability_dex[ability_key] = ability

    def get_ability(self, key):
        if key not in self.ability_dex.keys():
            print("Key '" + key + "' not found in ability dex.")
            return key

        return self.ability_dex[key]