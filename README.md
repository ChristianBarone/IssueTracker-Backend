# issueTracker

**Aplicació web per gestionar Issues per a l'assignatura ASW QP 2025-26**

# Autors
ID de grup: it115
****
**Andreu Caro** ``andreu.percy.caro@estudiantat.upc.edu``<br>
**Martí Piris Grau** ``marti.piris@estudiantat.upc.edu`` <br>
**Hala Alkhatib** ``hala.alkhatib@estudiantat.upc.edu`` <br>
**Christian Alejandro Barone** ``christian.alejandro.barone@estudiantat.upc.edu`` <br>
**Aleks Shahverdyan** ``aleks.shahverdyan@estudiantat.upc.edu``

# Instruccions de configuració local

1. Instal·lar Docker
2. Afegir els arxius de configuració d'entorn als directoris corresponents
3. Des del directori arrel, executar: 
``` 
(Linux) $ sudo docker compose --project-directory docker-services/ up -d
```
4. Quan s'hagi inicialitzat podràs accedir a la base de dades PostgreSQL mitjançant DBeaver o un altre gestor de bases de dades. <br>
<br>
- <strong>Host: </strong> localhost
- <strong>Port: </strong> 5432
- <strong>Usuari: </strong> postgres
- <strong>Contrasenya: </strong> postgres
- <strong>Database: </strong> issueTrackerDB
