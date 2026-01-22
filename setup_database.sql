-- Criar banco de dados
CREATE DATABASE IF NOT EXISTS inundacoes_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Criar usuário (ALTERE A SENHA!)
CREATE USER IF NOT EXISTS 'lnzila'@'localhost' IDENTIFIED BY 'inunda123!';

-- Conceder privilégios
GRANT ALL PRIVILEGES ON inundacoes_db.* TO 'lnzila'@'localhost';
FLUSH PRIVILEGES;

-- Usar o banco
USE inundacoes_db;

-- Tabela de Províncias
CREATE TABLE IF NOT EXISTS provinces (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    risk VARCHAR(20) NOT NULL,
    population INT NOT NULL,
    area DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_risk (risk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Municípios
CREATE TABLE IF NOT EXISTS municipalities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    province_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    population INT NOT NULL,
    area DECIMAL(10,2) NOT NULL,
    risk VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (province_id) REFERENCES provinces(id) ON DELETE CASCADE,
    INDEX idx_province (province_id),
    INDEX idx_name (name),
    INDEX idx_risk (risk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Bairros
CREATE TABLE IF NOT EXISTS bairros (
    id INT PRIMARY KEY AUTO_INCREMENT,
    municipality_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    population INT NOT NULL,
    type VARCHAR(50) NOT NULL,
    risk VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (municipality_id) REFERENCES municipalities(id) ON DELETE CASCADE,
    INDEX idx_municipality (municipality_id),
    INDEX idx_name (name),
    INDEX idx_risk (risk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Simulações (Histórico)
CREATE TABLE IF NOT EXISTS simulations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    level VARCHAR(20) NOT NULL,
    province VARCHAR(100),
    municipality VARCHAR(100),
    bairro VARCHAR(100),
    flood_rate DECIMAL(5,2) NOT NULL,
    water_level DECIMAL(10,2),
    flooded_count INT NOT NULL,
    total_affected INT NOT NULL,
    total_analyzed INT NOT NULL,
    avg_risk DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_level (level),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Resultados por Área
CREATE TABLE IF NOT EXISTS simulation_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    simulation_id INT NOT NULL,
    area_name VARCHAR(100) NOT NULL,
    area_type VARCHAR(20) NOT NULL,
    flooded BOOLEAN NOT NULL,
    water_level DECIMAL(10,2) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    recovery_days INT NOT NULL,
    affected_population INT NOT NULL,
    total_population INT NOT NULL,
    elevation DECIMAL(10,2),
    elevation_min DECIMAL(10,2),
    elevation_max DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (simulation_id) REFERENCES simulations(id) ON DELETE CASCADE,
    INDEX idx_simulation (simulation_id),
    INDEX idx_flooded (flooded)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Inserir dados de Luanda
INSERT INTO provinces (id, name, risk, population, area) VALUES
(1, 'Luanda', 'Muito Alto', 8329517, 2417.00);

-- Inserir municípios de Luanda
INSERT INTO municipalities (id, province_id, name, population, area, risk) VALUES
(1, 1, 'Belas', 600000, 500.00, 'Alto'),
(2, 1, 'Cacuaco', 850000, 450.00, 'Muito Alto'),
(3, 1, 'Cazenga', 980000, 32.00, 'Muito Alto'),
(4, 1, 'Icolo e Bengo', 150000, 3600.00, 'Médio'),
(5, 1, 'Luanda', 2200000, 116.00, 'Muito Alto'),
(6, 1, 'Quiçama', 25000, 13900.00, 'Baixo'),
(7, 1, 'Viana', 2000000, 1700.00, 'Alto'),
(8, 1, 'Kilamba Kiaxi', 1800000, 189.00, 'Muito Alto'),
(9, 1, 'Talatona', 500000, 160.00, 'Médio'),
(10, 1, 'Maianga', 500000, 50.00, 'Alto'),
(11, 1, 'Rangel', 261000, 62.00, 'Muito Alto'),
(12, 1, 'Ingombota', 370000, 30.00, 'Médio'),
(13, 1, 'Samba', 400000, 345.00, 'Alto'),
(14, 1, 'Sambizanga', 300000, 40.00, 'Muito Alto');

-- Inserir bairros de Belas
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(1, 'Belas Sede', 180000, 'Residencial', 'Médio'),
(1, 'Benfica', 140000, 'Residencial', 'Alto'),
(1, 'Ramiros', 95000, 'Residencial', 'Baixo');

-- Insirir bairros de Cacuaco
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(2, 'Kikolo', 180000, 'Residencial', 'Muito Alto'),
(2, 'Sequele', 140000, 'Residencial', 'Alto'),
(2, 'Funda', 160000, 'Residencial', 'Alto'),
(2, 'Quiage', 95000, 'Residencial', 'Médio'),
(2, 'Cabolombo', 110000, 'Residencial', 'Alto');

-- Inserir bairros de Cazenga
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(3, 'Hoji-ya-Henda', 220000, 'Residencial', 'Muito Alto'),
(3, 'Tala Hady', 180000, 'Residencial', 'Alto'),
(3, 'Cazenga Sede', 250000, 'Residencial', 'Muito Alto'),
(3, 'Sapu', 150000, 'Residencial', 'Alto');

-- Inserir bairros de Luanda (município central)
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(5, 'Ingombota', 150000, 'Comercial', 'Médio'),
(5, 'Maianga', 180000, 'Residencial', 'Alto'),
(5, 'Rangel', 220000, 'Residencial', 'Alto'),
(5, 'Sambizanga', 280000, 'Residencial', 'Muito Alto'),
(5, 'Ilha de Luanda', 45000, 'Turístico', 'Muito Alto'),
(5, 'Maculusso', 90000, 'Residencial', 'Baixo'),
(5, 'Alvalade', 120000, 'Residencial', 'Médio'),
(5, 'Mutamba', 80000, 'Comercial', 'Alto');


-- Inserir bairros de Viana
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(7, 'Viana Sede', 250000, 'Residencial', 'Alto'),
(7, 'Calumbo', 180000, 'Residencial', 'Médio'),
(7, 'Catete', 120000, 'Residencial', 'Médio'),
(7, 'Kikuxi', 200000, 'Industrial', 'Alto'),
(7, 'Zango', 350000, 'Residencial', 'Muito Alto');

-- Inserir bairros do Kilamba Kiaxi
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(8, 'Golfe', 300000, 'Residencial', 'Alto'),
(8, 'Palanca', 280000, 'Residencial', 'Alto'),
(8, 'Kilamba', 450000, 'Residencial', 'Médio'),
(8, 'Camama', 320000, 'Residencial', 'Alto'),
(8, 'Sapu', 150000, 'Residencial', 'Alto'),
(8, 'Nova Vida', 200000, 'Residencial', 'Médio'),
(8, 'Bairro Popular', 250000, 'Residencial', 'Alto'),
(8, 'Morro Bento', 220000, 'Residencial', 'Alto'),
(8, 'Projecto Nova Vida', 150000, 'Residencial', 'Baixo');

-- Inserir bairros de Maianga
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(10, 'Alvalade', 120000, 'Residencial', 'Médio'),
(10, 'Bairro Popular', 250000, 'Residencial', 'Alto'),
(10, 'Cassenda', 150000, 'Residencial', 'Alto'),
(10, 'Cassequel', 100000, 'Residencial', 'Médio'),
(10, 'Mártires do Kifangondo', 80000, 'Residencial', 'Alto'),
(10, 'Prenda', 200000, 'Residencial', 'Muito Alto'),
(10, 'Rocha Pinto', 180000, 'Residencial', 'Alto'),
(10, 'Catambor', 90000, 'Residencial', 'Médio'),
(10, 'Catinton', 110000, 'Residencial', 'Alto'),
(10, 'Calemba', 70000, 'Residencial', 'Baixo');

-- Inserir bairros de Rangel
iNSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(11, 'Terra Nova', 100000, 'Residencial', 'Alto'),
(11, 'Precol', 80000, 'Residencial', 'Muito Alto'),
(11, 'Combatentes', 120000, 'Residencial', 'Alto'),
(11, 'Valódia', 90000, 'Residencial', 'Médio'),
(11, 'Mabor', 70000, 'Residencial', 'Alto'),
(11, 'Cuca', 60000, 'Residencial', 'Médio'),
(11, 'Triangulo', 50000, 'Residencial', 'Baixo'),
(11, 'Comandante Valódia', 110000, 'Residencial', 'Alto'),
(11, 'Lixeira', 95000, 'Residencial', 'Muito Alto'),
(11, 'S. Pedro', 85000, 'Residencial', 'Médio');

-- Inseriri bairros de Ingombota
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(12, 'Azul', 80000, 'Residencial', 'Médio'),
(12, 'Boa Vista', 60000, 'Residencial', 'Baixo'),
(12, 'Bungo', 70000, 'Residencial', 'Alto'),
(12, 'Chicala I', 50000, 'Residencial', 'Médio'),
(12, 'Chicala II', 45000, 'Residencial', 'Alto'),
(12, 'Cidade Alta', 90000, 'Comercial', 'Baixo'),
(12, 'Coqueiros', 120000, 'Residencial', 'Médio'),
(12, 'Coreia', 100000, 'Residencial', 'Alto'),
(12, 'Cruzeiro', 85000, 'Comercial', 'Médio'),
(12, 'Patrice Lumumba', 110000, 'Residencial', 'Alto');

-- Inserir bairros de Samba
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(13, 'Rocha Pinto', 150000, 'Residencial', 'Alto'),
(13, 'Prenda', 200000, 'Residencial', 'Muito Alto'),
(13, 'Gamek', 180000, 'Residencial', 'Alto'),
(13, 'Morro Bento', 220000, 'Residencial', 'Médio'),
(13, 'Mabunda', 90000, 'Residencial', 'Alto'),
(13, 'Corimba', 120000, 'Residencial', 'Muito Alto'),
(13, 'Bairro Azul', 100000, 'Residencial', 'Médio'),
(13, 'Samba Pequena', 80000, 'Residencial', 'Baixo'),
(13, 'Coreia', 95000, 'Residencial', 'Alto'),
(13, 'Cassenda', 110000, 'Residencial', 'Médio');

-- Inserir bairros de Sambizanga
INSERT INTO bairros (municipality_id, name, population, type, risk) VALUES
(14, 'Bairro Operário', 150000, 'Residencial', 'Muito Alto'),
(14, 'Ngola Kiluanje', 120000, 'Residencial', 'Alto'),
(14, 'Miramar', 80000, 'Residencial', 'Médio'),
(14, 'Comandante Valódia', 100000, 'Residencial', 'Alto'),
(14, 'Lixeira', 90000, 'Residencial', 'Muito Alto'),
(14, 'S. Pedro', 70000, 'Residencial', 'Médio'),
(14, 'Petrangol', 110000, 'Residencial', 'Alto'),
(14, 'Boavista', 60000, 'Residencial', 'Baixo'),
(14, 'EMCIB', 85000, 'Residencial', 'Médio'),
(14, 'Uíge', 95000, 'Residencial', 'Alto');


-- Verificar instalação
SELECT 'Banco de dados configurado com sucesso!' as status;
SELECT COUNT(*) as total_bairros FROM bairros;
SELECT COUNT(*) as total_municipios FROM municipalities;
SELECT COUNT(*) as total_provincias FROM provinces;
