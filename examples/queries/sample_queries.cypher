// Sample Cypher Queries for Neo4j MCP
// ==================================

// Schema exploration queries
// --------------------------

// List all node labels
CALL db.labels();

// List all relationship types
CALL db.relationshipTypes();

// List all property keys
CALL db.propertyKeys();

// Show database constraints
SHOW CONSTRAINTS;

// Show database indexes
SHOW INDEXES;

// Basic data exploration
// ----------------------

// Count all nodes in the database
MATCH (n) RETURN count(n) as total_nodes;

// Count nodes by label
MATCH (n)
RETURN labels(n) as label, count(n) as count
ORDER BY count DESC;

// Count relationships by type
MATCH ()-[r]->()
RETURN type(r) as relationship_type, count(r) as count
ORDER BY count DESC;

// Sample data creation (Movie Graph)
// ---------------------------------

// Create some sample persons
CREATE (keanu:Person {name: "Keanu Reeves", born: 1964})
CREATE (laurence:Person {name: "Laurence Fishburne", born: 1961})
CREATE (carrie:Person {name: "Carrie-Anne Moss", born: 1967})
CREATE (lana:Person {name: "Lana Wachowski", born: 1965})
CREATE (lilly:Person {name: "Lilly Wachowski", born: 1967});

// Create a movie
CREATE (matrix:Movie {title: "The Matrix", released: 1999, tagline: "Welcome to the Real World"});

// Create relationships
MATCH (keanu:Person {name: "Keanu Reeves"}), (matrix:Movie {title: "The Matrix"})
CREATE (keanu)-[:ACTED_IN {roles: ["Neo"]}]->(matrix);

MATCH (laurence:Person {name: "Laurence Fishburne"}), (matrix:Movie {title: "The Matrix"})
CREATE (laurence)-[:ACTED_IN {roles: ["Morpheus"]}]->(matrix);

MATCH (carrie:Person {name: "Carrie-Anne Moss"}), (matrix:Movie {title: "The Matrix"})
CREATE (carrie)-[:ACTED_IN {roles: ["Trinity"]}]->(matrix);

MATCH (lana:Person {name: "Lana Wachowski"}), (matrix:Movie {title: "The Matrix"})
CREATE (lana)-[:DIRECTED]->(matrix);

MATCH (lilly:Person {name: "Lilly Wachowski"}), (matrix:Movie {title: "The Matrix"})
CREATE (lilly)-[:DIRECTED]->(matrix);

// Query examples
// --------------

// Find all actors in The Matrix
MATCH (person:Person)-[:ACTED_IN]->(movie:Movie {title: "The Matrix"})
RETURN person.name as actor, movie.title as movie;

// Find all movies directed by Lana Wachowski
MATCH (director:Person {name: "Lana Wachowski"})-[:DIRECTED]->(movie:Movie)
RETURN movie.title as movie, movie.released as year;

// Find actors and their roles
MATCH (person:Person)-[r:ACTED_IN]->(movie:Movie)
RETURN person.name as actor, movie.title as movie, r.roles as roles;

// Find co-actors (actors who appeared in the same movie)
MATCH (actor1:Person)-[:ACTED_IN]->(movie:Movie)<-[:ACTED_IN]-(actor2:Person)
WHERE actor1 <> actor2
RETURN actor1.name as actor1, actor2.name as actor2, movie.title as movie;

// Advanced queries
// ----------------

// Find actors born in the 1960s
MATCH (person:Person)
WHERE person.born >= 1960 AND person.born < 1970
RETURN person.name as name, person.born as birth_year
ORDER BY person.born;

// Find the degree of separation between actors
MATCH path = shortestPath((actor1:Person {name: "Keanu Reeves"})-[*]-(actor2:Person {name: "Carrie-Anne Moss"}))
RETURN length(path) as degrees_of_separation, 
       [n in nodes(path) | n.name] as path_names;

// Aggregation example - count movies per decade
MATCH (movie:Movie)
WITH movie.released - (movie.released % 10) as decade, count(movie) as movie_count
RETURN decade as decade, movie_count
ORDER BY decade;

// Update examples
// ---------------

// Add a new property to all Person nodes
MATCH (p:Person)
SET p.updated = timestamp();

// Update a specific person's information
MATCH (p:Person {name: "Keanu Reeves"})
SET p.nickname = "The One";

// Delete examples (be careful!)
// -----------------------------

// Delete a specific relationship
MATCH (p:Person {name: "Keanu Reeves"})-[r:ACTED_IN]->(m:Movie {title: "The Matrix"})
DELETE r;

// Delete a node and all its relationships
MATCH (p:Person {name: "Keanu Reeves"})
DETACH DELETE p;

// Clean up - remove all sample data
MATCH (n:Person) DETACH DELETE n;
MATCH (n:Movie) DETACH DELETE n; 