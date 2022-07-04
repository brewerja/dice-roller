package dieroll.controllers;

import dieroll.models.Message;
import dieroll.models.Roll;
import dieroll.models.RollRequest;
import org.springframework.beans.factory.annotation.Autowired;
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
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import java.time.Instant;
import java.util.Arrays;
import java.util.Random;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Controller
public class RollController {

    private static final Random RANDOM = new Random();
    private static final Pattern ROLL_PATTERN = Pattern.compile("^[\\d,]{1,60}$");

    @Autowired
    JedisPool jedisPool;

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
        Roll roll = new Roll(roomId, rollRequest.name(), Instant.now().toEpochMilli(), rollRequest.request(), result);
        persistRollToRedis(roll);
        return roll;
    }

    private void persistRollToRedis(Roll roll) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.zadd(roll.roomId().getBytes(), roll.timestamp(), roll.getBytes());
        }
    }

    @MessageMapping("/message/{roomId}")
    @SendTo("/topic/messages/{roomId}")
    public Message talk(@DestinationVariable String roomId, Message message) {
        return message;
    }

    @GetMapping("/rooms/{roomId}")
    public ModelAndView rooms(@PathVariable String roomId, Model model) {
        model.addAttribute("roomId", roomId);
        return new ModelAndView("room");
    }
}
