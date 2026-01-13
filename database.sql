BEGIN TRANSACTION;
CREATE TABLE "group" (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description TEXT, 
	monthly_contribution INTEGER NOT NULL, 
	created_by INTEGER NOT NULL, 
	created_at DATETIME, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(created_by) REFERENCES user (id)
);
INSERT INTO "group" VALUES(1,'Étudiants solidaires','Groupe d’entraide pour étudiants en difficulté financière.
Aide ponctuelle pour frais scolaires et logement.',10,2,'2025-12-16 12:02:38.908709',0);
INSERT INTO "group" VALUES(2,'Collègues de travail','Mutuelle entre collègues pour imprévus personnels.
Soutien financier rapide sans recours au crédit.',10,2,'2025-12-16 12:03:24.734669',0);
INSERT INTO "group" VALUES(3,'Voisins solidaires','Groupe de quartier pour entraide locale.
Aide santé et catastrophes domestiques.',10,2,'2025-12-16 12:04:01.981869',0);
INSERT INTO "group" VALUES(4,'Amis proches','Groupe de solidarité entre amis pour couvrir les urgences de santé et situations imprévues.',10,3,'2025-12-16 12:08:55.801439',0);
CREATE TABLE membership (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	group_id INTEGER NOT NULL, 
	balance INTEGER NOT NULL, 
	joined_at DATETIME, 
	auto_pay BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id)
);
INSERT INTO "membership" VALUES(1,2,1,50,'2025-12-16 12:02:38.942933',1);
INSERT INTO "membership" VALUES(2,2,2,80,'2025-12-16 12:03:24.746137',1);
INSERT INTO "membership" VALUES(3,2,3,150,'2025-12-16 12:04:02.024824',1);
INSERT INTO "membership" VALUES(4,3,3,0,'2025-12-16 12:05:54.348192',1);
INSERT INTO "membership" VALUES(5,3,2,0,'2025-12-16 12:05:58.160010',1);
INSERT INTO "membership" VALUES(6,3,4,100,'2025-12-16 12:08:55.816452',1);
INSERT INTO "membership" VALUES(7,4,4,0,'2025-12-20 18:59:47.835263',1);
INSERT INTO "membership" VALUES(8,4,1,0,'2025-12-20 19:00:04.180902',1);
INSERT INTO "membership" VALUES(9,4,3,0,'2025-12-20 19:00:11.796052',1);
INSERT INTO "membership" VALUES(10,4,2,0,'2025-12-20 19:00:15.638895',1);
CREATE TABLE notification (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	group_id INTEGER, 
	type VARCHAR(30) NOT NULL, 
	message VARCHAR(255) NOT NULL, 
	date DATETIME, 
	read BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id)
);
INSERT INTO "notification" VALUES(1,1,1,'group_created','Groupe ''Étudiants solidaires'' créé','2025-12-16 12:02:38.958074',0);
INSERT INTO "notification" VALUES(2,1,2,'group_created','Groupe ''Collègues de travail'' créé','2025-12-16 12:03:24.758183',0);
INSERT INTO "notification" VALUES(3,1,3,'group_created','Groupe ''Voisins solidaires'' créé','2025-12-16 12:04:02.037018',0);
INSERT INTO "notification" VALUES(4,2,3,'contribution_paid','Cotisation de 50 MAD payée (Simulation Stripe)','2025-12-16 12:04:14.617729',0);
INSERT INTO "notification" VALUES(5,1,3,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #2','2025-12-16 12:04:14.637239',0);
INSERT INTO "notification" VALUES(6,2,2,'contribution_paid','Cotisation de 20 MAD payée (Simulation Stripe)','2025-12-16 12:04:29.934115',0);
INSERT INTO "notification" VALUES(7,1,2,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #2','2025-12-16 12:04:29.947851',0);
INSERT INTO "notification" VALUES(8,2,1,'contribution_paid','Cotisation de 10 MAD payée (Simulation Stripe)','2025-12-16 12:04:40.384987',0);
INSERT INTO "notification" VALUES(9,1,1,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #2','2025-12-16 12:04:40.400771',0);
INSERT INTO "notification" VALUES(10,3,3,'group_join','Vous avez rejoint le groupe ''Voisins solidaires''','2025-12-16 12:05:54.395729',0);
INSERT INTO "notification" VALUES(11,1,3,'group_join','sal.ma a rejoint le groupe ''Voisins solidaires''','2025-12-16 12:05:54.409133',0);
INSERT INTO "notification" VALUES(12,3,2,'group_join','Vous avez rejoint le groupe ''Collègues de travail''','2025-12-16 12:05:58.193820',0);
INSERT INTO "notification" VALUES(13,1,2,'group_join','sal.ma a rejoint le groupe ''Collègues de travail''','2025-12-16 12:05:58.205979',0);
INSERT INTO "notification" VALUES(14,3,3,'contribution_paid','Cotisation de 50 MAD payée (Simulation PayPal)','2025-12-16 12:06:12.815031',0);
INSERT INTO "notification" VALUES(15,1,3,'contribution_paid','Cotisation simulée via PayPal pour utilisateur #3','2025-12-16 12:06:12.827682',0);
INSERT INTO "notification" VALUES(16,3,2,'contribution_due','Cotisation de 10 MAD due pour Collègues de travail','2025-12-16 12:06:51.870970',0);
INSERT INTO "notification" VALUES(17,3,3,'contribution_paid','Cotisation de 50 MAD payée (Simulation Stripe)','2025-12-16 12:06:58.149339',0);
INSERT INTO "notification" VALUES(18,1,3,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #3','2025-12-16 12:06:58.161973',0);
INSERT INTO "notification" VALUES(19,3,3,'tx_approved','Transaction approuvée','2025-12-16 12:07:24.670572',0);
INSERT INTO "notification" VALUES(20,3,2,'tx_approved','Transaction approuvée','2025-12-16 12:07:25.703248',0);
INSERT INTO "notification" VALUES(21,3,3,'tx_approved','Transaction approuvée','2025-12-16 12:07:26.350169',0);
INSERT INTO "notification" VALUES(22,2,1,'tx_approved','Transaction approuvée','2025-12-16 12:07:26.994461',0);
INSERT INTO "notification" VALUES(23,2,2,'tx_approved','Transaction approuvée','2025-12-16 12:07:27.664083',0);
INSERT INTO "notification" VALUES(24,2,3,'tx_approved','Transaction approuvée','2025-12-16 12:07:28.341813',0);
INSERT INTO "notification" VALUES(25,1,4,'group_created','Groupe ''Amis proches'' créé','2025-12-16 12:08:55.829554',0);
INSERT INTO "notification" VALUES(26,3,4,'contribution_paid','Cotisation de 100 MAD payée (Simulation PayPal)','2025-12-16 12:09:15.719987',0);
INSERT INTO "notification" VALUES(27,1,4,'contribution_paid','Cotisation simulée via PayPal pour utilisateur #3','2025-12-16 12:09:15.733290',0);
INSERT INTO "notification" VALUES(28,3,4,'tx_approved','Transaction approuvée','2025-12-16 12:09:29.485890',0);
INSERT INTO "notification" VALUES(29,1,3,'aid_request','Demande d’aide de ch elot pour 2000 MAD — Motif: Suite à un dégât des eaux dans mon logement, j’ai dû effectuer des réparations urgentes.
Cette aide me permettra de couvrir une partie des frais nécessaires.','2025-12-16 12:16:57.713514',0);
INSERT INTO "notification" VALUES(30,3,4,'tx_approved','Transaction approuvée','2025-12-16 13:25:37.148562',0);
INSERT INTO "notification" VALUES(31,3,3,'tx_approved','Transaction approuvée','2025-12-16 13:25:39.173821',0);
INSERT INTO "notification" VALUES(32,3,2,'tx_approved','Transaction approuvée','2025-12-16 13:25:40.051794',0);
INSERT INTO "notification" VALUES(33,3,3,'tx_approved','Transaction approuvée','2025-12-16 13:25:40.859887',0);
INSERT INTO "notification" VALUES(34,2,3,'tx_approved','Transaction approuvée','2025-12-16 13:25:43.454061',0);
INSERT INTO "notification" VALUES(35,2,2,'tx_approved','Transaction approuvée','2025-12-16 13:25:44.620185',0);
INSERT INTO "notification" VALUES(36,2,3,'contribution_paid','Cotisation de 20 MAD payée (Simulation PayPal)','2025-12-16 14:07:53.898147',0);
INSERT INTO "notification" VALUES(37,1,3,'contribution_paid','Cotisation simulée via PayPal pour utilisateur #2','2025-12-16 14:07:53.931355',0);
INSERT INTO "notification" VALUES(38,2,3,'contribution_paid','Cotisation de 20 MAD payée (Simulation PayPal)','2025-12-20 18:51:50.902892',0);
INSERT INTO "notification" VALUES(39,1,3,'contribution_paid','Cotisation simulée via PayPal pour utilisateur #2','2025-12-20 18:51:50.921031',0);
INSERT INTO "notification" VALUES(40,2,1,'contribution_paid','Cotisation de 50 MAD payée (Simulation Stripe)','2025-12-20 18:52:03.782974',0);
INSERT INTO "notification" VALUES(41,1,1,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #2','2025-12-20 18:52:03.799354',0);
INSERT INTO "notification" VALUES(42,3,4,'contribution_paid','Cotisation de 20 MAD payée (Simulation Stripe)','2025-12-20 18:56:47.567197',0);
INSERT INTO "notification" VALUES(43,1,4,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #3','2025-12-20 18:56:47.586561',0);
INSERT INTO "notification" VALUES(44,3,2,'contribution_paid','Cotisation de 50 MAD payée (Simulation PayPal)','2025-12-20 18:57:13.766387',0);
INSERT INTO "notification" VALUES(45,1,2,'contribution_paid','Cotisation simulée via PayPal pour utilisateur #3','2025-12-20 18:57:13.784089',0);
INSERT INTO "notification" VALUES(46,3,2,'tx_approved','Transaction approuvée','2025-12-20 18:57:32.148629',0);
INSERT INTO "notification" VALUES(47,3,4,'tx_approved','Transaction approuvée','2025-12-20 18:57:33.187695',0);
INSERT INTO "notification" VALUES(48,2,1,'tx_approved','Transaction approuvée','2025-12-20 18:57:33.946822',0);
INSERT INTO "notification" VALUES(49,2,3,'tx_approved','Transaction approuvée','2025-12-20 18:57:34.684643',0);
INSERT INTO "notification" VALUES(50,2,3,'tx_approved','Transaction approuvée','2025-12-20 18:57:38.011560',0);
INSERT INTO "notification" VALUES(51,4,4,'group_join','Vous avez rejoint le groupe ''Amis proches''','2025-12-20 18:59:47.880131',0);
INSERT INTO "notification" VALUES(52,1,4,'group_join','moh ma a rejoint le groupe ''Amis proches''','2025-12-20 18:59:47.899114',0);
INSERT INTO "notification" VALUES(53,4,1,'group_join','Vous avez rejoint le groupe ''Étudiants solidaires''','2025-12-20 19:00:04.230152',0);
INSERT INTO "notification" VALUES(54,1,1,'group_join','moh ma a rejoint le groupe ''Étudiants solidaires''','2025-12-20 19:00:04.247496',0);
INSERT INTO "notification" VALUES(55,4,3,'group_join','Vous avez rejoint le groupe ''Voisins solidaires''','2025-12-20 19:00:11.812285',0);
INSERT INTO "notification" VALUES(56,1,3,'group_join','moh ma a rejoint le groupe ''Voisins solidaires''','2025-12-20 19:00:11.830546',0);
INSERT INTO "notification" VALUES(57,4,2,'group_join','Vous avez rejoint le groupe ''Collègues de travail''','2025-12-20 19:00:15.692003',0);
INSERT INTO "notification" VALUES(58,1,2,'group_join','moh ma a rejoint le groupe ''Collègues de travail''','2025-12-20 19:00:15.721931',0);
INSERT INTO "notification" VALUES(59,4,4,'contribution_paid','Cotisation de 50 MAD payée (Simulation Stripe)','2025-12-20 19:00:26.251039',0);
INSERT INTO "notification" VALUES(60,1,4,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #4','2025-12-20 19:00:26.266620',0);
INSERT INTO "notification" VALUES(61,4,3,'contribution_paid','Cotisation de 20 MAD payée (Simulation Stripe)','2025-12-20 19:00:34.361016',0);
INSERT INTO "notification" VALUES(62,1,3,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #4','2025-12-20 19:00:34.379724',0);
INSERT INTO "notification" VALUES(63,4,2,'contribution_paid','Cotisation de 20 MAD payée (Simulation PayPal)','2025-12-20 19:00:44.354967',0);
INSERT INTO "notification" VALUES(64,1,2,'contribution_paid','Cotisation simulée via PayPal pour utilisateur #4','2025-12-20 19:00:44.372199',0);
INSERT INTO "notification" VALUES(65,4,1,'contribution_paid','Cotisation de 20 MAD payée (Simulation Stripe)','2025-12-20 19:00:52.749967',0);
INSERT INTO "notification" VALUES(66,1,1,'contribution_paid','Cotisation simulée via Stripe pour utilisateur #4','2025-12-20 19:00:52.767603',0);
CREATE TABLE policy (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	description TEXT, 
	contribution FLOAT NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE "transaction" (
	id INTEGER NOT NULL, 
	group_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	amount INTEGER NOT NULL, 
	type VARCHAR(20) NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	reason VARCHAR(255), 
	date DATETIME, 
	provider VARCHAR(20), 
	external_id VARCHAR(120), 
	PRIMARY KEY (id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);
INSERT INTO "transaction" VALUES(1,3,2,50,'cotisation','approved',NULL,'2025-12-16 12:04:14.560012','stripe',NULL);
INSERT INTO "transaction" VALUES(2,2,2,20,'cotisation','approved',NULL,'2025-12-16 12:04:29.921175','stripe',NULL);
INSERT INTO "transaction" VALUES(3,1,2,10,'cotisation','approved',NULL,'2025-12-16 12:04:40.346900','stripe',NULL);
INSERT INTO "transaction" VALUES(4,3,3,50,'cotisation','approved',NULL,'2025-12-16 12:06:12.760385','paypal',NULL);
INSERT INTO "transaction" VALUES(5,2,3,10,'cotisation','approved',NULL,'2025-12-16 12:06:51.855587',NULL,NULL);
INSERT INTO "transaction" VALUES(6,3,3,50,'cotisation','approved',NULL,'2025-12-16 12:06:58.116557','stripe',NULL);
INSERT INTO "transaction" VALUES(7,4,3,100,'cotisation','approved',NULL,'2025-12-16 12:09:15.663733','paypal',NULL);
INSERT INTO "transaction" VALUES(8,3,2,2000,'aide','pending','Suite à un dégât des eaux dans mon logement, j’ai dû effectuer des réparations urgentes.
Cette aide me permettra de couvrir une partie des frais nécessaires.','2025-12-16 12:16:57.699981',NULL,NULL);
INSERT INTO "transaction" VALUES(9,3,2,20,'cotisation','approved',NULL,'2025-12-16 14:07:53.872272','paypal',NULL);
INSERT INTO "transaction" VALUES(10,3,2,20,'cotisation','approved',NULL,'2025-12-20 18:51:50.878833','paypal',NULL);
INSERT INTO "transaction" VALUES(11,1,2,50,'cotisation','approved',NULL,'2025-12-20 18:52:03.766444','stripe',NULL);
INSERT INTO "transaction" VALUES(12,4,3,20,'cotisation','approved',NULL,'2025-12-20 18:56:47.549906','stripe',NULL);
INSERT INTO "transaction" VALUES(13,2,3,50,'cotisation','approved',NULL,'2025-12-20 18:57:13.709048','paypal',NULL);
INSERT INTO "transaction" VALUES(14,4,4,50,'cotisation','pending',NULL,'2025-12-20 19:00:26.201449','stripe',NULL);
INSERT INTO "transaction" VALUES(15,3,4,20,'cotisation','pending',NULL,'2025-12-20 19:00:34.348091','stripe',NULL);
INSERT INTO "transaction" VALUES(16,2,4,20,'cotisation','pending',NULL,'2025-12-20 19:00:44.339987','paypal',NULL);
INSERT INTO "transaction" VALUES(17,1,4,20,'cotisation','pending',NULL,'2025-12-20 19:00:52.690232','stripe',NULL);
CREATE TABLE user (
	id INTEGER NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(10) NOT NULL, 
	created_at DATETIME, 
	failed_attempts INTEGER NOT NULL, 
	lock_until DATETIME, 
	is_blocked BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	UNIQUE (email)
);
INSERT INTO "user" VALUES(1,'admin','admin@mytakaful.com','scrypt:32768:8:1$sQLynarrLxSC7syD$aac8d4d55e74ab3fd8187ee99484a7c63c9efe211fb5dea2edf4171c2438fd5778af3cc2f66d06e021259b7c9598f447d121b375d1e450cb9e84eb7a0eac8e40','admin','2025-12-16 11:54:28.499836',0,NULL,0);
INSERT INTO "user" VALUES(2,'ch elot','chocho10@gmail.com','scrypt:32768:8:1$mSzs8iJZxFsF8qMJ$8da665ed3bd82b1e86f2d588f315b2f7eddcbdb0fb2429718b0a37be7172b410f4b0cdc359d91a68e63253ae7e31d41860e66151a9e40627beac8b7b88251126','user','2025-12-16 12:00:22.760739',0,NULL,0);
INSERT INTO "user" VALUES(3,'sal.ma','sal.ma10@gmail.com','scrypt:32768:8:1$W7k6t7TUYvXByJG2$d84c2b14fabe1cc41469689e2cc24cad4927747640996015d37a09d74724cc736fbe9757cd787bdf5aa1f487f2a2154ec76e2f726dd4251df59e49ae6410a94c','user','2025-12-16 12:05:22.254667',0,NULL,0);
INSERT INTO "user" VALUES(4,'moh ma','moh.10@gmail.com','scrypt:32768:8:1$PWue19EhJJXGbdxf$54e5c96b0c86d6fe92b92d05b851bb2af1041c2cb6de650dae67984657597b1244c72b1bfbd712ec94d94bdfbb8db6bc39a8fd45203e968ab5bf655cbbec499e','user','2025-12-20 18:59:40.516693',0,NULL,0);
COMMIT;
