-- MySQL dump 10.13  Distrib 8.4.13, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: seguimiento_egresados
-- ------------------------------------------------------
-- Server version	8.4.13

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `seguimiento_egresados`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `seguimiento_egresados` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `seguimiento_egresados`;

--
-- Table structure for table `asignaciones_personal`
--

DROP TABLE IF EXISTS `asignaciones_personal`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `asignaciones_personal` (
  `id_asignacion` int NOT NULL AUTO_INCREMENT,
  `id_personal` int NOT NULL,
  `id_rol` int NOT NULL,
  `id_programa` int DEFAULT NULL,
  `id_facultad` int DEFAULT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date DEFAULT NULL,
  `estado` enum('activo','inactivo') COLLATE utf8mb4_unicode_ci DEFAULT 'activo',
  PRIMARY KEY (`id_asignacion`),
  KEY `fk_asignacion_personal` (`id_personal`),
  KEY `fk_asignacion_rol` (`id_rol`),
  KEY `fk_asignacion_programa` (`id_programa`),
  KEY `fk_asignacion_facultad` (`id_facultad`),
  CONSTRAINT `fk_asignacion_facultad` FOREIGN KEY (`id_facultad`) REFERENCES `facultades` (`id_facultad`),
  CONSTRAINT `fk_asignacion_personal` FOREIGN KEY (`id_personal`) REFERENCES `personal` (`id_personal`) ON DELETE CASCADE,
  CONSTRAINT `fk_asignacion_programa` FOREIGN KEY (`id_programa`) REFERENCES `programas_estudio` (`id_programa`),
  CONSTRAINT `fk_asignacion_rol` FOREIGN KEY (`id_rol`) REFERENCES `roles` (`id_rol`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `asignaciones_personal`
--

LOCK TABLES `asignaciones_personal` WRITE;
/*!40000 ALTER TABLE `asignaciones_personal` DISABLE KEYS */;
INSERT INTO `asignaciones_personal` VALUES (3,4,4,3,NULL,'2026-11-16',NULL,'activo'),(4,3,3,NULL,3,'2026-11-16',NULL,'activo');
/*!40000 ALTER TABLE `asignaciones_personal` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `certificados`
--

DROP TABLE IF EXISTS `certificados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `certificados` (
  `id_certificado` int NOT NULL AUTO_INCREMENT,
  `id_egresado` int NOT NULL,
  `nombre` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `institucion_emisora` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo` enum('externo','interno') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'externo',
  `categoria` enum('curso','capacitacion','diplomado','idioma','otro') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'curso',
  `nivel_idioma` enum('basico','intermedio','avanzado') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_emision` date DEFAULT NULL,
  `url_credencial` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ruta_archivo` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_certificado`),
  KEY `fk_cert_egresado` (`id_egresado`),
  CONSTRAINT `fk_cert_egresado` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `certificados`
--

LOCK TABLES `certificados` WRITE;
/*!40000 ALTER TABLE `certificados` DISABLE KEYS */;
/*!40000 ALTER TABLE `certificados` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `curriculas`
--

DROP TABLE IF EXISTS `curriculas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `curriculas` (
  `id_curricula` int NOT NULL AUTO_INCREMENT,
  `id_programa` int NOT NULL,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `anio_inicio` year DEFAULT NULL,
  `anio_fin` year DEFAULT NULL,
  `estado` enum('activo','inactivo') COLLATE utf8mb4_unicode_ci DEFAULT 'activo',
  PRIMARY KEY (`id_curricula`),
  KEY `fk_curricula_programa` (`id_programa`),
  CONSTRAINT `fk_curricula_programa` FOREIGN KEY (`id_programa`) REFERENCES `programas_estudio` (`id_programa`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `curriculas`
--

LOCK TABLES `curriculas` WRITE;
/*!40000 ALTER TABLE `curriculas` DISABLE KEYS */;
INSERT INTO `curriculas` VALUES (1,2,'17A2ESSP',2018,NULL,'activo'),(2,3,'17A4SI',NULL,NULL,'activo');
/*!40000 ALTER TABLE `curriculas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `egresados`
--

DROP TABLE IF EXISTS `egresados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `egresados` (
  `id_egresado` int NOT NULL AUTO_INCREMENT,
  `codigo_universitario` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dni` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `apellido_paterno` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `apellido_materno` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `nombres` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `genero` char(1) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_nacimiento` date DEFAULT NULL,
  `correo_institucional` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `correo_personal` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `telefono` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `domicilio` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `distrito` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `provincia` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pais` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Perú',
  `linkedin` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `facebook` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tiktok` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `foto` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_curricula` int NOT NULL,
  `anio_ingreso` year DEFAULT NULL,
  `periodo` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `anio_egreso` year DEFAULT NULL,
  `es_bachiller` tinyint(1) NOT NULL DEFAULT '0',
  `es_titulado` tinyint(1) NOT NULL DEFAULT '0',
  `tiene_maestria` tinyint(1) NOT NULL DEFAULT '0',
  `tiene_doctorado` tinyint(1) NOT NULL DEFAULT '0',
  `tiene_phd` tinyint(1) NOT NULL DEFAULT '0',
  `nivel_maximo` enum('egresado','bachiller','titulado','maestria','doctorado','phd') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'egresado',
  `titulo_cv` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `perfil_profesional` text COLLATE utf8mb4_unicode_ci,
  `creado_en` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_egresado`),
  UNIQUE KEY `dni` (`dni`),
  UNIQUE KEY `codigo_universitario` (`codigo_universitario`),
  KEY `fk_egresado_curricula` (`id_curricula`),
  CONSTRAINT `fk_egresado_curricula` FOREIGN KEY (`id_curricula`) REFERENCES `curriculas` (`id_curricula`),
  CONSTRAINT `egresados_chk_1` CHECK ((`genero` in (_utf8mb4'M',_utf8mb4'F')))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `egresados`
--

LOCK TABLES `egresados` WRITE;
/*!40000 ALTER TABLE `egresados` DISABLE KEYS */;
INSERT INTO `egresados` VALUES (1,'1802293030','71491995','ONQUE','ROBLES','Angie Ines','F','2001-02-05','angieines@undac.edu.pe',NULL,NULL,'Barrio Besada S/N La Quinua ',NULL,NULL,NULL,'Perú',NULL,NULL,NULL,NULL,1,2018,NULL,NULL,0,0,0,0,0,'egresado',NULL,NULL,'2026-11-08 23:25:06'),(2,'2144403193','74824912','OLAZO','DIAZ','Fiorella Aracely','F','2003-05-24','olazo@undac.edu.pe','','','ESTANCIA PARAN S/N COMUNID. CAMPESINA SAN ANTONIO DE RANCAS','','','','Perú','','','','uploads/fotos/1dccd65a9279d36de1287ba63b11eb3f.png',2,2021,NULL,NULL,0,0,0,0,0,'egresado',NULL,NULL,'2026-11-17 05:12:35');
/*!40000 ALTER TABLE `egresados` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `empleos`
--

DROP TABLE IF EXISTS `empleos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `empleos` (
  `id_empleo` int NOT NULL AUTO_INCREMENT,
  `id_egresado` int NOT NULL,
  `id_empresa` int NOT NULL,
  `cargo` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_contrato` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `funciones` text COLLATE utf8mb4_unicode_ci,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date DEFAULT NULL,
  `es_actual` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id_empleo`),
  KEY `fk_empleo_egresado` (`id_egresado`),
  KEY `fk_empleo_empresa` (`id_empresa`),
  CONSTRAINT `fk_empleo_egresado` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`),
  CONSTRAINT `fk_empleo_empresa` FOREIGN KEY (`id_empresa`) REFERENCES `empresas` (`id_empresa`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `empleos`
--

LOCK TABLES `empleos` WRITE;
/*!40000 ALTER TABLE `empleos` DISABLE KEYS */;
/*!40000 ALTER TABLE `empleos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `empresas`
--

DROP TABLE IF EXISTS `empresas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `empresas` (
  `id_empresa` int NOT NULL AUTO_INCREMENT,
  `ruc` char(11) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `razon_social` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre_comercial` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_sector` int NOT NULL,
  `tipo_empresa` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `direccion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `distrito` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `provincia` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pais` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Perú',
  `telefono` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sitio_web` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` enum('activa','pendiente') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'activa',
  `sugerido_por` int DEFAULT NULL,
  PRIMARY KEY (`id_empresa`),
  UNIQUE KEY `ruc` (`ruc`),
  KEY `fk_empresa_sector` (`id_sector`),
  KEY `fk_empresa_egresado` (`sugerido_por`),
  CONSTRAINT `fk_empresa_egresado` FOREIGN KEY (`sugerido_por`) REFERENCES `egresados` (`id_egresado`) ON DELETE SET NULL,
  CONSTRAINT `fk_empresa_sector` FOREIGN KEY (`id_sector`) REFERENCES `sectores` (`id_sector`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `empresas`
--

LOCK TABLES `empresas` WRITE;
/*!40000 ALTER TABLE `empresas` DISABLE KEYS */;
INSERT INTO `empresas` VALUES (1,NULL,'[DEMO] Organización Tecnología Pasco','[DEMO] Tecnología Pasco',1,NULL,NULL,NULL,NULL,NULL,'Perú',NULL,NULL,'activa',NULL),(2,NULL,'[DEMO] Centro Servicios Profesionales','[DEMO] Centro Profesional',2,NULL,NULL,NULL,NULL,NULL,'Perú',NULL,NULL,'activa',NULL);
/*!40000 ALTER TABLE `empresas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `encuestas`
--

DROP TABLE IF EXISTS `encuestas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `encuestas` (
  `id_encuesta` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` text COLLATE utf8mb4_unicode_ci,
  `anio` year NOT NULL,
  `estado` enum('borrador','publicada','cerrada') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'borrador',
  `fecha_inicio` date DEFAULT NULL,
  `fecha_fin` date DEFAULT NULL,
  PRIMARY KEY (`id_encuesta`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `encuestas`
--

LOCK TABLES `encuestas` WRITE;
/*!40000 ALTER TABLE `encuestas` DISABLE KEYS */;
INSERT INTO `encuestas` VALUES (1,'Encuesta de seguimiento de egresados',NULL,2026,'publicada','2026-11-09','2026-11-10');
/*!40000 ALTER TABLE `encuestas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `facultades`
--

DROP TABLE IF EXISTS `facultades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `facultades` (
  `id_facultad` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `codigo` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` enum('activo','inactivo') COLLATE utf8mb4_unicode_ci DEFAULT 'activo',
  PRIMARY KEY (`id_facultad`),
  UNIQUE KEY `nombre` (`nombre`),
  UNIQUE KEY `codigo` (`codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `facultades`
--

LOCK TABLES `facultades` WRITE;
/*!40000 ALTER TABLE `facultades` DISABLE KEYS */;
INSERT INTO `facultades` VALUES (2,'Facultad de Ciencias de la Educación',NULL,'activo'),(3,'Facultad de Ingeniería',NULL,'activo');
/*!40000 ALTER TABLE `facultades` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `habilidades`
--

DROP TABLE IF EXISTS `habilidades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `habilidades` (
  `id_habilidad` int NOT NULL AUTO_INCREMENT,
  `id_egresado` int NOT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo` enum('habilidad','interes') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'habilidad',
  PRIMARY KEY (`id_habilidad`),
  KEY `fk_habilidad_egresado` (`id_egresado`),
  CONSTRAINT `fk_habilidad_egresado` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `habilidades`
--

LOCK TABLES `habilidades` WRITE;
/*!40000 ALTER TABLE `habilidades` DISABLE KEYS */;
/*!40000 ALTER TABLE `habilidades` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ofertas_guardadas`
--

DROP TABLE IF EXISTS `ofertas_guardadas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ofertas_guardadas` (
  `id_guardado` int NOT NULL AUTO_INCREMENT,
  `id_egresado` int NOT NULL,
  `id_oferta` int NOT NULL,
  `fecha` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_guardado`),
  UNIQUE KEY `uq_guardado_egresado_oferta` (`id_egresado`,`id_oferta`),
  KEY `ix_guardado_oferta` (`id_oferta`),
  CONSTRAINT `fk_guardado_egresado` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`) ON DELETE CASCADE,
  CONSTRAINT `fk_guardado_oferta` FOREIGN KEY (`id_oferta`) REFERENCES `ofertas_laborales` (`id_oferta`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ofertas_guardadas`
--

LOCK TABLES `ofertas_guardadas` WRITE;
/*!40000 ALTER TABLE `ofertas_guardadas` DISABLE KEYS */;
INSERT INTO `ofertas_guardadas` VALUES (2,1,2,'2026-11-09 01:07:46');
/*!40000 ALTER TABLE `ofertas_guardadas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ofertas_laborales`
--

DROP TABLE IF EXISTS `ofertas_laborales`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ofertas_laborales` (
  `id_oferta` int NOT NULL AUTO_INCREMENT,
  `id_creado_por` int DEFAULT NULL,
  `id_empresa` int DEFAULT NULL,
  `titulo` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `telefono` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `descripcion` text COLLATE utf8mb4_unicode_ci,
  `requisitos` text COLLATE utf8mb4_unicode_ci,
  `modalidad` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo_oferta` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jornada` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remuneracion` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `funciones` text COLLATE utf8mb4_unicode_ci,
  `ubicacion` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ruta_imagen` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `url_original` text COLLATE utf8mb4_unicode_ci,
  `fuente` enum('manual','automatico') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'manual',
  `fecha_publicacion` date NOT NULL DEFAULT (curdate()),
  `fecha_vencimiento` date NOT NULL,
  `activa` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_oferta`),
  KEY `fk_oferta_personal` (`id_creado_por`),
  KEY `fk_oferta_empresa` (`id_empresa`),
  CONSTRAINT `fk_oferta_empresa` FOREIGN KEY (`id_empresa`) REFERENCES `empresas` (`id_empresa`),
  CONSTRAINT `fk_oferta_personal` FOREIGN KEY (`id_creado_por`) REFERENCES `personal` (`id_personal`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ofertas_laborales`
--

LOCK TABLES `ofertas_laborales` WRITE;
/*!40000 ALTER TABLE `ofertas_laborales` DISABLE KEYS */;
INSERT INTO `ofertas_laborales` VALUES (1,1,1,'[DEMO] Analista de datos junior','[DEMO] Tecnología Pasco',NULL,'Convocatoria ficticia para comprobar el modulo de oportunidades y postulaciones.','Manejo basico de SQL; conocimientos de dashboards.','Híbrido',NULL,NULL,NULL,NULL,'Pasco',NULL,NULL,'manual','2026-11-08','2027-01-07',1),(2,1,2,'[DEMO] Asistente administrativo','[DEMO] Centro Profesional',NULL,'Convocatoria ficticia para demostrar filtros de todo el Peru.','Conocimientos de herramientas ofimaticas.','Presencial',NULL,NULL,NULL,NULL,'Lima',NULL,NULL,'manual','2026-11-08','2027-01-07',1);
/*!40000 ALTER TABLE `ofertas_laborales` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `opciones`
--

DROP TABLE IF EXISTS `opciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `opciones` (
  `id_opcion` int NOT NULL AUTO_INCREMENT,
  `id_pregunta` int NOT NULL,
  `texto` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `orden` int NOT NULL,
  PRIMARY KEY (`id_opcion`),
  KEY `id_pregunta` (`id_pregunta`),
  CONSTRAINT `opciones_ibfk_1` FOREIGN KEY (`id_pregunta`) REFERENCES `preguntas` (`id_pregunta`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `opciones`
--

LOCK TABLES `opciones` WRITE;
/*!40000 ALTER TABLE `opciones` DISABLE KEYS */;
/*!40000 ALTER TABLE `opciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `personal`
--

DROP TABLE IF EXISTS `personal`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `personal` (
  `id_personal` int NOT NULL AUTO_INCREMENT,
  `nombres` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `apellido_paterno` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `apellido_materno` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `correo` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `telefono` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` enum('activo','inactivo') COLLATE utf8mb4_unicode_ci DEFAULT 'activo',
  PRIMARY KEY (`id_personal`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `personal`
--

LOCK TABLES `personal` WRITE;
/*!40000 ALTER TABLE `personal` DISABLE KEYS */;
INSERT INTO `personal` VALUES (1,'Administrador','Sistema','UNDAC',NULL,NULL,'activo'),(2,'Pedro','Mendoza','Sanchez',NULL,NULL,'activo'),(3,'Liker','Porras','Cardenas',NULL,NULL,'activo'),(4,'Pit','Lurdes','Ferroso',NULL,NULL,'activo');
/*!40000 ALTER TABLE `personal` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `postulaciones`
--

DROP TABLE IF EXISTS `postulaciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `postulaciones` (
  `id_postulacion` int NOT NULL AUTO_INCREMENT,
  `id_egresado` int NOT NULL,
  `id_oferta` int NOT NULL,
  `mensaje` text COLLATE utf8mb4_unicode_ci,
  `estado` enum('enviada','en_revision','seleccionado','no_seleccionado') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'enviada',
  `fecha` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_postulacion`),
  UNIQUE KEY `uq_postulacion_egresado_oferta` (`id_egresado`,`id_oferta`),
  KEY `ix_postulacion_oferta` (`id_oferta`),
  CONSTRAINT `fk_postulacion_egresado` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`) ON DELETE CASCADE,
  CONSTRAINT `fk_postulacion_oferta` FOREIGN KEY (`id_oferta`) REFERENCES `ofertas_laborales` (`id_oferta`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `postulaciones`
--

LOCK TABLES `postulaciones` WRITE;
/*!40000 ALTER TABLE `postulaciones` DISABLE KEYS */;
INSERT INTO `postulaciones` VALUES (1,1,1,'Interés en la convocatoria registrada en NEXO UNDAC','en_revision','2026-11-09 01:07:52');
/*!40000 ALTER TABLE `postulaciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `preguntas`
--

DROP TABLE IF EXISTS `preguntas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `preguntas` (
  `id_pregunta` int NOT NULL AUTO_INCREMENT,
  `id_encuesta` int NOT NULL,
  `texto` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo` enum('texto','numero','si_no','opcion_unica','opcion_multiple') COLLATE utf8mb4_unicode_ci NOT NULL,
  `orden` int NOT NULL,
  `obligatoria` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id_pregunta`),
  KEY `id_encuesta` (`id_encuesta`),
  CONSTRAINT `preguntas_ibfk_1` FOREIGN KEY (`id_encuesta`) REFERENCES `encuestas` (`id_encuesta`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `preguntas`
--

LOCK TABLES `preguntas` WRITE;
/*!40000 ALTER TABLE `preguntas` DISABLE KEYS */;
INSERT INTO `preguntas` VALUES (1,1,'Que tan efectivo en la carrera en el campo laboral','numero',1,1);
/*!40000 ALTER TABLE `preguntas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `programas_estudio`
--

DROP TABLE IF EXISTS `programas_estudio`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `programas_estudio` (
  `id_programa` int NOT NULL AUTO_INCREMENT,
  `id_facultad` int NOT NULL,
  `nombre` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `codigo` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` enum('activo','inactivo') COLLATE utf8mb4_unicode_ci DEFAULT 'activo',
  PRIMARY KEY (`id_programa`),
  UNIQUE KEY `codigo` (`codigo`),
  KEY `fk_programa_facultad` (`id_facultad`),
  CONSTRAINT `fk_programa_facultad` FOREIGN KEY (`id_facultad`) REFERENCES `facultades` (`id_facultad`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `programas_estudio`
--

LOCK TABLES `programas_estudio` WRITE;
/*!40000 ALTER TABLE `programas_estudio` DISABLE KEYS */;
INSERT INTO `programas_estudio` VALUES (2,2,'Ciencias Sociales, Filosofía y Psicología Educativa',NULL,'activo'),(3,3,'Ingeniería de Sistemas y Computación',NULL,'activo');
/*!40000 ALTER TABLE `programas_estudio` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `respuestas`
--

DROP TABLE IF EXISTS `respuestas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `respuestas` (
  `id_respuesta` int NOT NULL AUTO_INCREMENT,
  `id_encuesta` int NOT NULL,
  `id_egresado` int DEFAULT NULL,
  `id_pregunta` int NOT NULL,
  `id_opcion` int DEFAULT NULL,
  `respuesta_texto` text COLLATE utf8mb4_unicode_ci,
  `respuesta_numero` decimal(10,2) DEFAULT NULL,
  `respuesta_booleana` tinyint(1) DEFAULT NULL,
  `fecha_respuesta` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_respuesta`),
  KEY `id_encuesta` (`id_encuesta`),
  KEY `id_pregunta` (`id_pregunta`),
  KEY `id_opcion` (`id_opcion`),
  KEY `id_egresado` (`id_egresado`),
  CONSTRAINT `respuestas_ibfk_1` FOREIGN KEY (`id_encuesta`) REFERENCES `encuestas` (`id_encuesta`),
  CONSTRAINT `respuestas_ibfk_2` FOREIGN KEY (`id_pregunta`) REFERENCES `preguntas` (`id_pregunta`),
  CONSTRAINT `respuestas_ibfk_3` FOREIGN KEY (`id_opcion`) REFERENCES `opciones` (`id_opcion`),
  CONSTRAINT `respuestas_ibfk_4` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `respuestas`
--

LOCK TABLES `respuestas` WRITE;
/*!40000 ALTER TABLE `respuestas` DISABLE KEYS */;
INSERT INTO `respuestas` VALUES (1,1,1,1,NULL,NULL,5.00,NULL,'2026-11-10 03:26:45');
/*!40000 ALTER TABLE `respuestas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `id_rol` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descripcion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_rol`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `roles`
--

LOCK TABLES `roles` WRITE;
/*!40000 ALTER TABLE `roles` DISABLE KEYS */;
INSERT INTO `roles` VALUES (1,'administrador','Administra el sistema'),(2,'utsag','Gestiona el seguimiento institucional de egresados'),(3,'coordinador','Coordina el seguimiento en una facultad'),(4,'docente_responsable','Responsable del seguimiento de un programa'),(5,'egresado','Usuario egresado');
/*!40000 ALTER TABLE `roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sectores`
--

DROP TABLE IF EXISTS `sectores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sectores` (
  `id_sector` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id_sector`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sectores`
--

LOCK TABLES `sectores` WRITE;
/*!40000 ALTER TABLE `sectores` DISABLE KEYS */;
INSERT INTO `sectores` VALUES (2,'[DEMO] Servicios profesionales'),(1,'[DEMO] Tecnologia');
/*!40000 ALTER TABLE `sectores` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `seguimiento_externo`
--

DROP TABLE IF EXISTS `seguimiento_externo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `seguimiento_externo` (
  `id_seguimiento` int NOT NULL AUTO_INCREMENT,
  `id_egresado` int NOT NULL,
  `id_oferta` int NOT NULL,
  `estado` enum('visitado','postulado','entrevista','contratacion_reportada','no_seleccionado','desistio') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'visitado',
  `visitas` int NOT NULL DEFAULT '0',
  `observacion` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_postulacion` date DEFAULT NULL,
  `fecha_contratacion` date DEFAULT NULL,
  `creado_en` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `actualizado_en` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_seguimiento`),
  UNIQUE KEY `uq_seg_externo_persona_oferta` (`id_egresado`,`id_oferta`),
  KEY `ix_seguimiento_externo_estado` (`estado`),
  KEY `ix_seguimiento_externo_actualizado` (`actualizado_en`),
  KEY `fk_v9_seg_oferta` (`id_oferta`),
  CONSTRAINT `fk_v9_seg_egresado` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`) ON DELETE CASCADE,
  CONSTRAINT `fk_v9_seg_oferta` FOREIGN KEY (`id_oferta`) REFERENCES `ofertas_laborales` (`id_oferta`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `seguimiento_externo`
--

LOCK TABLES `seguimiento_externo` WRITE;
/*!40000 ALTER TABLE `seguimiento_externo` DISABLE KEYS */;
/*!40000 ALTER TABLE `seguimiento_externo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `trayectoria_academica`
--

DROP TABLE IF EXISTS `trayectoria_academica`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trayectoria_academica` (
  `id_trayectoria` int NOT NULL AUTO_INCREMENT,
  `id_egresado` int NOT NULL,
  `tipo` enum('bachiller','titulado','maestria','doctorado','phd') COLLATE utf8mb4_unicode_ci NOT NULL,
  `grado_titulo` varchar(300) COLLATE utf8mb4_unicode_ci NOT NULL,
  `institucion` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Universidad Nacional Daniel Alcides Carrión',
  `fecha_obtencion` date NOT NULL,
  `fuente` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'SUNEDU',
  PRIMARY KEY (`id_trayectoria`),
  KEY `fk_tray_egresado` (`id_egresado`),
  CONSTRAINT `fk_tray_egresado` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `trayectoria_academica`
--

LOCK TABLES `trayectoria_academica` WRITE;
/*!40000 ALTER TABLE `trayectoria_academica` DISABLE KEYS */;
/*!40000 ALTER TABLE `trayectoria_academica` ENABLE KEYS */;
UNLOCK TABLES;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `actualizar_nivel_egresado` AFTER INSERT ON `trayectoria_academica` FOR EACH ROW BEGIN
    UPDATE egresados 
    SET 
        es_bachiller   = IF(NEW.tipo IN ('bachiller','titulado','maestria','doctorado','phd'), 1, es_bachiller),
        es_titulado    = IF(NEW.tipo IN ('titulado','maestria','doctorado','phd'), 1, es_titulado),
        tiene_maestria = IF(NEW.tipo IN ('maestria','doctorado','phd'), 1, tiene_maestria),
        tiene_doctorado= IF(NEW.tipo IN ('doctorado','phd'), 1, tiene_doctorado),
        tiene_phd      = IF(NEW.tipo = 'phd', 1, tiene_phd),
        
        nivel_maximo = CASE 
            WHEN NEW.tipo = 'phd' THEN 'phd'
            WHEN NEW.tipo = 'doctorado' AND nivel_maximo != 'phd' THEN 'doctorado'
            WHEN NEW.tipo = 'maestria'  AND nivel_maximo NOT IN ('doctorado', 'phd') THEN 'maestria'
            WHEN NEW.tipo = 'titulado'  AND nivel_maximo NOT IN ('maestria', 'doctorado', 'phd') THEN 'titulado'
            WHEN NEW.tipo = 'bachiller' AND nivel_maximo = 'egresado' THEN 'bachiller'
            ELSE nivel_maximo
        END
    WHERE id_egresado = NEW.id_egresado;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `usuario_roles`
--

DROP TABLE IF EXISTS `usuario_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario_roles` (
  `id_usuario_rol` int NOT NULL AUTO_INCREMENT,
  `id_usuario` int NOT NULL,
  `id_rol` int NOT NULL,
  PRIMARY KEY (`id_usuario_rol`),
  UNIQUE KEY `id_usuario` (`id_usuario`,`id_rol`),
  KEY `fk_uroles_roles` (`id_rol`),
  CONSTRAINT `fk_uroles_roles` FOREIGN KEY (`id_rol`) REFERENCES `roles` (`id_rol`),
  CONSTRAINT `fk_uroles_usuarios` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuario_roles`
--

LOCK TABLES `usuario_roles` WRITE;
/*!40000 ALTER TABLE `usuario_roles` DISABLE KEYS */;
INSERT INTO `usuario_roles` VALUES (1,1,1),(2,2,5),(3,3,2),(7,4,3),(6,5,4),(8,6,5);
/*!40000 ALTER TABLE `usuario_roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id_usuario` int NOT NULL AUTO_INCREMENT,
  `correo` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contrasena_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_egresado` int DEFAULT NULL,
  `id_personal` int DEFAULT NULL,
  `ultimo_acceso` datetime DEFAULT NULL,
  `estado` enum('activo','inactivo') COLLATE utf8mb4_unicode_ci DEFAULT 'activo',
  `token_recuperacion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `token_expiracion` datetime DEFAULT NULL,
  `ultimo_cambio_password` datetime DEFAULT NULL,
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `correo` (`correo`),
  KEY `id_egresado` (`id_egresado`),
  KEY `id_personal` (`id_personal`),
  CONSTRAINT `usuarios_ibfk_1` FOREIGN KEY (`id_egresado`) REFERENCES `egresados` (`id_egresado`),
  CONSTRAINT `usuarios_ibfk_2` FOREIGN KEY (`id_personal`) REFERENCES `personal` (`id_personal`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,'admin@undac.edu.pe','$2b$12$5FNamzMBek1K0xAsVo8/y.OtG153H0jebSfZBHKICSVvtSJPo/1rC',NULL,1,'2026-11-17 20:43:24','activo',NULL,NULL,NULL),(2,'angieines@undac.edu.pe','$2b$12$VnC7bytkWn5TJ9vXWQWYUeAdUuLDlV3dS2LsdzkppK6xXYzPaBD12',1,NULL,'2026-11-12 12:39:03','activo',NULL,NULL,NULL),(3,'pedrosanchez@undac.edu.pe','$2b$12$MEQwiDpPSayCY.ROEzbOLOvy9qfeWx8pCtAkJ7vZSS/urkIvI2jOe',NULL,2,'2026-11-17 20:46:49','activo',NULL,NULL,NULL),(4,'liker@undac.edu.pe','$2b$12$gcA6Ow0vSc5T/z4xjrpVae8AKHfcmK8zZCDP.c0WdGebPPloeFcHi',NULL,3,'2026-11-17 20:49:04','activo',NULL,NULL,NULL),(5,'ferroso@undac.edu.pe','$2b$12$Cp1YakW9J81viYQN.juIl./7gOzUqYJiJwLwvVPUnjlKcN90TmoIq',NULL,4,'2026-11-17 20:50:26','activo',NULL,NULL,NULL),(6,'olazo@undac.edu.pe','$2b$12$eujdMB7GocwT.7WLFx7eJeoRo7FNv3irI5ZRswL4fN2YQSvAZwxYe',2,NULL,'2026-11-17 20:51:55','activo',NULL,NULL,NULL);
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'seguimiento_egresados'
--

--
-- Dumping routines for database 'seguimiento_egresados'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-20 13:59:37
