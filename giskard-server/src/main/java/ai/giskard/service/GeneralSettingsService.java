package ai.giskard.service;

import ai.giskard.domain.GeneralSettings;
import ai.giskard.domain.SerializedGiskardGeneralSettings;
import ai.giskard.repository.GeneralSettingsRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
@RequiredArgsConstructor
public class GeneralSettingsService {
    private final Logger log = LoggerFactory.getLogger(GeneralSettingsService.class);

    private final GeneralSettingsRepository settingsRepository;

    public GeneralSettings getSettings() {
        return deserializeSettings(settingsRepository.getById(SerializedGiskardGeneralSettings.SINGLE_ID).getSettings());
    }

    public GeneralSettings save(GeneralSettings settings) {
        SerializedGiskardGeneralSettings entity = new SerializedGiskardGeneralSettings(serializeSettings(settings));
        return deserializeSettings(settingsRepository.save(entity).getSettings());
    }

    public void saveIfNotExists(GeneralSettings settings) {
        Optional<SerializedGiskardGeneralSettings> result = settingsRepository.findById(SerializedGiskardGeneralSettings.SINGLE_ID);
        if (result.isEmpty()) {
            save(settings);
            log.info("Saved general settings: {}", settings);
        }
    }

    private GeneralSettings deserializeSettings(String serializedSettings) {
        try {
            return new ObjectMapper().readValue(serializedSettings, GeneralSettings.class);
        } catch (JsonProcessingException e) {
            throw new GiskardRuntimeException("Failed to deserialize general settings", e);
        }
    }

    private String serializeSettings(GeneralSettings settings) {
        String serializedSettings;
        try {
            serializedSettings = new ObjectMapper().writeValueAsString(settings);
        } catch (JsonProcessingException e) {
            throw new GiskardRuntimeException("Failed to serialize general settings", e);
        }
        return serializedSettings;
    }
}
