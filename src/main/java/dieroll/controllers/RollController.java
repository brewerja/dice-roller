package dieroll.controllers;

import dieroll.models.Message;
import dieroll.models.Roll;
import dieroll.models.RollRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.ModelAndView;

import java.security.SecureRandom;
import java.time.Instant;
import java.util.Arrays;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Controller
public class RollController {

    private static final SecureRandom RANDOM = new SecureRandom();
    private static final Pattern ROLL_PATTERN = Pattern.compile("^[\\d,]{1,60}$");

    @Autowired
    RedisTemplate<String, Roll> redisTemplate;

    @MessageMapping("/roll/{roomId}")
    @SendTo("/topic/rolls/{roomId}")
    public Roll roll(@DestinationVariable String roomId, RollRequest rollRequest) {
        if (!ROLL_PATTERN.matcher(rollRequest.request()).matches())
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Bad roll string");
        String result = Arrays.stream(rollRequest.request().split(","))
                .filter(s -> !s.isEmpty())
                .map(numSides -> RANDOM.nextInt(Integer.parseInt(numSides)) + 1)
                .map(Object::toString)
                .collect(Collectors.joining(","));
        Roll roll = new Roll(roomId, rollRequest.name(), Instant.now().toEpochMilli(), rollRequest.getRequestDisplay(), result);
        persistRollToRedis(roll);
        return roll;
    }

    private void persistRollToRedis(Roll roll) {
        redisTemplate.opsForZSet().add(roll.roomId(), roll, roll.timestamp());
    }

    @MessageMapping("/message/{roomId}")
    @SendTo("/topic/messages/{roomId}")
    public Message talk(@DestinationVariable String roomId, Message message) {
        return new Message(roomId, message.name(), Instant.now().toEpochMilli(), message.message());
    }

    @GetMapping("/rooms/{roomId}")
    public ModelAndView rooms(@PathVariable String roomId, Model model) {
        model.addAttribute("roomId", roomId);
        model.addAttribute("savedRolls", getRoomRolls(roomId));
        return new ModelAndView("room");
    }

    private Set<Roll> getRoomRolls(String roomId) {
        return redisTemplate.opsForZSet().range(roomId, -100, -1);
    }

}
