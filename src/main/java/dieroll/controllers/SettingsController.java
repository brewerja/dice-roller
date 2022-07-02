package dieroll.controllers;

import dieroll.SettingsConstants;
import dieroll.models.Settings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.Controller;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Objects;
import java.util.Properties;

@Controller
public class SettingsController implements InitializingBean {

    private static final Logger LOG = LoggerFactory.getLogger(SettingsController.class);

    @Value("${settingsPath}")
    private String settingsPath;

    @MessageMapping("/settings")
    @SendTo("/topic/settings")
    public Settings settings(Settings settings) throws Exception {
        Properties p = new Properties();
        createSettingsFileIfNotExisting();
        try (InputStream is = new FileInputStream(settingsPath)) {
            p.load(is);
        }
        if (settings.color() != null) {
            p.put(settings.name() + "." + SettingsConstants.COLOR, settings.color());
            try (OutputStream os = new FileOutputStream(settingsPath)) {
                p.store(os, null);
            }
        } else {
            String color = p.getProperty(settings.name() + "." + SettingsConstants.COLOR);
            settings = new Settings(settings.name(), Objects.requireNonNullElse(color, SettingsConstants.DEFAULT_COLOR));
        }
        return settings;
    }

    @Override
    public void afterPropertiesSet() throws Exception {
        if (settingsPath == null || settingsPath.isEmpty()) {
            LOG.error("No explicit settings path defined falling back to default.");
            File userDir = new File(System.getProperty("user.dir"));
            settingsPath = userDir.toPath().resolve("settings.properties").toAbsolutePath().toString();
        }
        LOG.info("Using settings path: " + settingsPath);
    }

    private synchronized void createSettingsFileIfNotExisting() throws IOException {
        Path settingsFile = Paths.get(settingsPath);
        if (!Files.exists(settingsFile)) {
            Files.createFile(settingsFile);
        }
    }

}
