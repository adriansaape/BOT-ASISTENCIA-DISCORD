"""
Tests para el cog de Recuperación
Ejecutar con: pytest tests/test_recuperacion.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import time, date
import discord
from discord.ext import commands

from cogs.recuperacion.commands import Recuperacion


# Fixtures para crear objetos mock de Discord
@pytest.fixture
def mock_bot():
    """Bot mock para los tests"""
    bot = MagicMock(spec=commands.Bot)
    bot.roles_recuperacion = {
        123456789: []  # Servidor de prueba sin restricciones
    }
    return bot


@pytest.fixture
def mock_guild():
    """Guild mock"""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    return guild


@pytest.fixture
def mock_channel():
    """Channel mock"""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 987654321
    return channel


@pytest.fixture
def mock_user():
    """User mock"""
    user = MagicMock(spec=discord.User)
    user.id = 111222333
    user.display_name = "Usuario Test"
    user.mention = "<@111222333>"
    user.roles = []
    return user


@pytest.fixture
def mock_interaction(mock_guild, mock_channel, mock_user):
    """Interaction mock completo"""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.channel = mock_channel
    interaction.user = mock_user
    interaction.client = MagicMock()
    interaction.client.roles_recuperacion = {123456789: []}
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction


@pytest.fixture
def recuperacion_cog(mock_bot):
    """Instancia del cog de recuperación"""
    return Recuperacion(mock_bot)


class TestComandoRecuperacion:
    """Tests para el comando /recuperación"""
    
    @pytest.mark.asyncio
    async def test_canal_no_permitido(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar si el canal no está permitido"""
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=False):
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            mock_interaction.response.defer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_usuario_no_registrado(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar si el usuario no está registrado"""
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=None):
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            mock_interaction.followup.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_horario_no_permitido(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar si está fuera del horario permitido"""
        hora_fuera_rango = time(10, 0)
        fecha_hoy = date.today()
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_fuera_rango
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert "Horario no permitido" in embed.title
    
    @pytest.mark.asyncio
    async def test_recuperacion_ya_registrada(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar si ya hay una recuperación hoy"""
        hora_permitida = time(15, 0)
        fecha_hoy = date.today()
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_permitida
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.verificar_recuperacion', return_value={'id': 1}), \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert "ya registrada" in embed.title.lower()
    
    @pytest.mark.asyncio
    async def test_registro_exitoso(self, recuperacion_cog, mock_interaction):
        """Test: Debe registrar correctamente una recuperación"""
        hora_permitida = time(15, 0)
        fecha_hoy = date.today()
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_permitida
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.verificar_recuperacion', return_value=None), \
             patch('cogs.recuperacion.commands.db') as mock_db, \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            mock_db.execute_query = AsyncMock(return_value=1)
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_db.execute_query.assert_called_once()
            call_args = mock_db.execute_query.call_args
            assert call_args[0][1][0] == 1
            assert call_args[0][1][1] == fecha_hoy
            assert call_args[0][1][2] == hora_permitida
            
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert "Registrada" in embed.title
            assert embed.color.value == 3066993
    
    @pytest.mark.asyncio
    async def test_horario_limite_inferior(self, recuperacion_cog, mock_interaction):
        """Test: Debe permitir el registro exactamente a las 14:30"""
        hora_limite = time(14, 30)
        fecha_hoy = date.today()
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_limite
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.verificar_recuperacion', return_value=None), \
             patch('cogs.recuperacion.commands.db') as mock_db, \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            mock_db.execute_query = AsyncMock(return_value=1)
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_db.execute_query.assert_called_once()
            mock_interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_horario_limite_superior(self, recuperacion_cog, mock_interaction):
        """Test: Debe permitir el registro exactamente a las 20:00"""
        hora_limite = time(20, 0)
        fecha_hoy = date.today()
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_limite
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.verificar_recuperacion', return_value=None), \
             patch('cogs.recuperacion.commands.db') as mock_db, \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            mock_db.execute_query = AsyncMock(return_value=1)
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_db.execute_query.assert_called_once()
            mock_interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_horario_antes_limite_inferior(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar el registro a las 14:29"""
        hora_antes = time(14, 29)
        fecha_hoy = date.today()
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_antes
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert "Horario no permitido" in embed.title
    
    @pytest.mark.asyncio
    async def test_horario_despues_limite_superior(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar el registro a las 20:01"""
        hora_despues = time(20, 1)
        fecha_hoy = date.today()
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_despues
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert "Horario no permitido" in embed.title
    
    @pytest.mark.asyncio
    async def test_verificar_query_insercion(self, recuperacion_cog, mock_interaction):
        """Test: Verificar que la query de inserción tiene los parámetros correctos"""
        hora_permitida = time(16, 30)
        fecha_hoy = date.today()
        practicante_id = 42
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_permitida
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=practicante_id), \
             patch('cogs.recuperacion.commands.verificar_recuperacion', return_value=None), \
             patch('cogs.recuperacion.commands.db') as mock_db, \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            mock_db.execute_query = AsyncMock(return_value=1)
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_db.execute_query.assert_called_once()
            call_args = mock_db.execute_query.call_args
            query = call_args[0][0]
            params = call_args[0][1]
            
            assert "INSERT INTO Recuperacion" in query
            assert "practicante_id" in query
            assert "fecha" in query
            assert "hora_entrada" in query
            assert params[0] == practicante_id
            assert params[1] == fecha_hoy
            assert params[2] == hora_permitida
    
    @pytest.mark.asyncio
    async def test_verificar_recuperacion_llamada_correcta(self, recuperacion_cog, mock_interaction):
        """Test: Verificar que verificar_recuperacion se llama con los parámetros correctos"""
        hora_permitida = time(17, 0)
        fecha_hoy = date.today()
        practicante_id = 99
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_permitida
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=practicante_id), \
             patch('cogs.recuperacion.commands.verificar_recuperacion') as mock_verificar, \
             patch('cogs.recuperacion.commands.db') as mock_db, \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_verificar.return_value = None
            mock_datetime.now.return_value = mock_datetime_obj
            mock_db.execute_query = AsyncMock(return_value=1)
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_verificar.assert_called_once_with(practicante_id, fecha_hoy)


class TestComandoHistorial:
    """Tests para el comando /recuperación_historial"""
    
    @pytest.mark.asyncio
    async def test_historial_canal_no_permitido(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar si el canal no está permitido"""
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=False):
            await recuperacion_cog.historial_recuperaciones.callback(recuperacion_cog, mock_interaction, dias=15)
            mock_interaction.response.defer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_historial_dias_invalidos(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar días fuera del rango"""
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1):
            
            # Test con días < 1
            await recuperacion_cog.historial_recuperaciones.callback(recuperacion_cog, mock_interaction, dias=0)
            mock_interaction.followup.send.assert_called_once()
            
            mock_interaction.followup.reset_mock()
            
            # Test con días > 30
            await recuperacion_cog.historial_recuperaciones.callback(recuperacion_cog, mock_interaction, dias=31)
            mock_interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_historial_vacio(self, recuperacion_cog, mock_interaction):
        """Test: Debe mostrar mensaje cuando no hay recuperaciones"""
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.db') as mock_db:
            
            mock_db.fetch_all = AsyncMock(return_value=[])
            
            await recuperacion_cog.historial_recuperaciones.callback(recuperacion_cog, mock_interaction, dias=15)
            
            # Verificar que se envió un embed informando que no hay datos
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert "no se encontraron" in embed.description.lower()
    
    @pytest.mark.asyncio
    async def test_historial_con_datos(self, recuperacion_cog, mock_interaction):
        """Test: Debe mostrar historial cuando hay recuperaciones"""
        datos_mock = [
            {
                'fecha': '12-05',
                'hora_entrada': time(15, 0),
                'hora_salida': time(18, 0)
            },
            {
                'fecha': '12-04',
                'hora_entrada': time(16, 0),
                'hora_salida': None
            }
        ]
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.db') as mock_db:
            
            mock_db.fetch_all = AsyncMock(return_value=datos_mock)
            
            await recuperacion_cog.historial_recuperaciones.callback(recuperacion_cog, mock_interaction, dias=15)
            
            # Verificar que se envió un embed con el historial
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            embed = call_args[1]['embed']
            assert "Historial" in embed.title
            assert len(embed.fields) == 2  # Dos recuperaciones


class TestValidacionRoles:
    """Tests para validación de roles"""
    
    @pytest.mark.asyncio
    async def test_roles_requeridos_sin_rol(self, recuperacion_cog, mock_interaction):
        """Test: Debe rechazar si se requieren roles y el usuario no los tiene"""
        mock_interaction.client.roles_recuperacion = {
            123456789: [999888777]  # Requiere un rol específico
        }
        mock_interaction.user.roles = []  # Usuario sin roles
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.verificar_rol_permitido', return_value=False):
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            mock_interaction.response.defer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_roles_requeridos_con_rol(self, recuperacion_cog, mock_interaction):
        """Test: Debe permitir si el usuario tiene el rol requerido"""
        mock_interaction.client.roles_recuperacion = {
            123456789: [999888777]
        }
        mock_role = MagicMock()
        mock_role.id = 999888777
        mock_interaction.user.roles = [mock_role]
        hora_permitida = time(15, 0)
        fecha_hoy = date.today()
        mock_datetime_obj = MagicMock()
        mock_datetime_obj.date.return_value = fecha_hoy
        mock_datetime_obj.time.return_value = hora_permitida
        
        with patch('cogs.recuperacion.commands.canal_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.verificar_rol_permitido', return_value=True), \
             patch('cogs.recuperacion.commands.obtener_practicante', return_value=1), \
             patch('cogs.recuperacion.commands.verificar_recuperacion', return_value=None), \
             patch('cogs.recuperacion.commands.db') as mock_db, \
             patch('cogs.recuperacion.commands.datetime') as mock_datetime:
            
            mock_datetime.now.return_value = mock_datetime_obj
            mock_db.execute_query = AsyncMock(return_value=1)
            
            await recuperacion_cog.recuperacion.callback(recuperacion_cog, mock_interaction)
            
            mock_interaction.response.defer.assert_called_once()


# Tests de integración rápida (sin mocks completos)
class TestIntegracionRapida:
    """Tests de integración rápida"""
    
    @pytest.mark.asyncio
    async def test_estructura_comando_recuperacion(self, recuperacion_cog):
        """Test: Verificar que el comando existe y tiene la estructura correcta"""
        assert hasattr(recuperacion_cog, 'recuperacion')
        assert hasattr(recuperacion_cog.recuperacion, 'callback')
        assert callable(recuperacion_cog.recuperacion.callback)
    
    @pytest.mark.asyncio
    async def test_estructura_comando_historial(self, recuperacion_cog):
        """Test: Verificar que el comando de historial existe"""
        assert hasattr(recuperacion_cog, 'historial_recuperaciones')
        assert hasattr(recuperacion_cog.historial_recuperaciones, 'callback')
        assert callable(recuperacion_cog.historial_recuperaciones.callback)

