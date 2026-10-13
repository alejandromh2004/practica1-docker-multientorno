CREATE TABLE IF NOT EXISTS pokemon (
    id SERIAL PRIMARY KEY,
    numero INT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    hp INT NOT NULL,
    ataque INT NOT NULL,
    imagen_url TEXT NOT NULL
);

INSERT INTO pokemon (numero, nombre, tipo, hp, ataque, imagen_url) VALUES
    (1, 'Bulbasaur', 'Planta / Veneno', 45, 49, 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png'),
    (4, 'Charmander', 'Fuego', 39, 52, 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png'),
    (7, 'Squirtle', 'Agua', 44, 48, 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png'),
    (25, 'Pikachu', 'Eléctrico', 35, 55, 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png'),
    (94, 'Gengar', 'Fantasma / Veneno', 60, 65, 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/94.png'),
    (143, 'Snorlax', 'Normal', 160, 110, 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/143.png');