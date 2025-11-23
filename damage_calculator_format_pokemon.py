from poke_env.data import GenData
from poke_env.battle.pokemon import Pokemon
from utils import UtilityFunctions

class DamageCalculatorFormatPokemon():
    def __init__(
        self,
        pokemon: Pokemon
    ) -> None:
        self.gen_data = GenData.from_gen(8)
        self.pokedex = self.gen_data.pokedex
        pokedex_entry = self.pokedex[pokemon.species]
        print(pokedex_entry)
        self.species = pokedex_entry.get('name')
        
        utils = UtilityFunctions()
        self.ability = utils.get_or_guess_ability(pokemon)

        if pokemon.item is None:
            # API requires a non-null value for hold item.
            self.item = "no_item"
        else:
            self.item = pokemon.item

        self.level = pokemon.level

    def formatted(self):
        return {
            "species": self.species, #species name AS IT IS IN THE POKEDEX  [REQUIRED]
            "ability": self.ability, #ability [REQUIRED]
            "item": self.item,  #item [REQUIRED]
            "level": self.level, #level [REQUIRED], must be a number
        }

