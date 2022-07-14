package dieroll.controllers;

import dieroll.models.Roll;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Set;

@RestController
public class RollsController {

    @Autowired
    RedisTemplate<String, Roll> redisTemplate;

    @GetMapping("/rooms/{roomId}/rolls")
    public Set<Roll> getRoomRolls(@PathVariable String roomId) {
        return redisTemplate.opsForZSet().range(roomId, -100, -1);
    }

}
